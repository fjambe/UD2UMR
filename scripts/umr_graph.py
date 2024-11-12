import re
import penman
from penman.exceptions import LayoutError
from umr_node import UMRNode

class UMRGraph:
    def __init__(self, ud_tree, deprels):
        """
        Initializes a UMRGraph instance to represent a sentence UMR graph.

        Attributes:
            ud_tree: The UD tree (Udapi Node).
            deprels (dict): A dictionary mapping UD dependency relations to UMR roles.
            self.root_var (str, optional): A variable representing the root of the UMR graph.
            self.nodes (list[UMRNode]): A list of UMRNode instances representing the nodes in the UMR graph.
            self.triples (list[tuple]): A list of triples that will form the UMR graph.
            self.track_conj (dict): A dictionary tracking conjunctions in the graph.
            self.extra_level (dict): A mapping of UMR nodes to additional parent nodes, mostly for abstract roles.

        Args:
            ud_tree: The UD tree representing syntactic dependencies in the sentence.
            deprels (dict): A dictionary mapping UD dependency relations to UMR roles.
        """
        self.ud_tree = ud_tree
        self.deprels = deprels
        self.root_var = None
        self.nodes: list[UMRNode] = []
        self.triples = []
        self.track_conj = {}
        self.extra_level = {}  # node: new_umr_parent, e.g. {var of ARG1: var of roleset-91}

    def __repr__(self):
        return f"Sentence(Text: '{self.ud_tree.text}', nodes={self.nodes})"

    @property
    def variable_names(self):
        """
        Returns:
            list: A list of 'var_name' values from each node in self.nodes.
        """
        return [node.var_name for node in self.nodes if hasattr(node, 'var_name')]

    def display_text(self):
        """Print out the text of the sentence."""
        print(f"SNT: {self.ud_tree.text}")

    def assign_variable_name(self, form):
        """
        Assign a unique variable name based on the first letter of ud_node.lemma.
        If a name is already taken, add a number suffix to make it unique.

        Args:
            form: The UD node with a 'lemma' attribute, or a string.

        Returns:
            str: A unique variable name.
        """
        first_letter = form.lemma[0].lower() if hasattr(form, 'lemma') else form[0].lower()
        count = 2

        if first_letter in self.variable_names:
            while f"{first_letter}{count}" in self.variable_names:
                count += 1

        var_name = first_letter if first_letter not in self.variable_names else f"{first_letter}{count}"
        lemma = form.lemma if hasattr(form, 'lemma') else form
        self.triples.append((var_name, 'instance', lemma))

        if not isinstance(form, str) and form.parent.is_root():
            self.root_var = var_name

        return var_name

    def correct_variable_name(self):
        """
        Return a list of triples with corrected variable naming, if necessary.
        Corrects variable names by organizing them by letter, ensuring sequential numbering.
        """
        var_pattern = re.compile(r"^([a-z])(\d*)$")
        var_groups = {}

        for var in self.variable_names:
            match = var_pattern.match(var)
            if match:
                base_letter = match.group(1)
                number = int(match.group(2)) if match.group(2) else 1
                var_groups.setdefault(base_letter, []).append((number, var))

        renaming_map = {}

        for base_letter, variables in var_groups.items():
            variables.sort()  # Sort by number

            for new_number, (current_number, var) in enumerate(variables, start=1):
                new_var = f"{base_letter}{new_number if new_number > 1 else ''}"

                if new_var != var:
                    renaming_map[var] = new_var

        corrected_triples = [
            (renaming_map.get(var, var), relation, renaming_map.get(value, value))
            for var, relation, value in self.triples
        ]

        return corrected_triples

    def remove_duplicate_triples(self):
        """ Removes duplicate triples from self.triples. """
        self.triples = list(set(self.triples))

    def reorder_triples(self):
        """
        Reorders the list of triples stored in `self.triples` based on a predefined hierarchy for the
        second element in each triple, in order to mirror the natural order of manual annotation.
        The ordering hierarchy is as follows:

        1. Triples with 'instance' as the second element have the highest priority.
        2. Triples with 'actor' or 'ARG1' as the second element are next in priority.
        3. Triples with 'patient' or 'ARG2' as the second element come after that.
        4. Next, triples with 'affectee' as the second element.
        5. Other elements not specifically listed (excluding 'refer-number' and 'refer-person').
        6. Finally, triples with 'aspect' come last among specified elements.
        7. 'refer-number' and 'refer-person' appear at the end.
        8. Roles named 'op1', 'op2', 'op3', etc., are ordered by increasing number (op1 has the highest priority).
        """

        hierarchy_order = {
            'instance': 0,
            'actor': 1,
            'patient': 2,
            'ARG1': 3,
            'ARG2': 4,
            'affectee': 5,
            'refer-person': 6,
            'refer-number': 7,
            'aspect': 8
        }

        def get_priority(triple):
            role = triple[1]

            if role.startswith('op'):
                try:
                    op_number = int(role[2:])
                    return 9 + op_number
                except ValueError:
                    return 10

            return hierarchy_order.get(role, 10)

        self.triples = sorted(self.triples, key=get_priority)

    def postprocessing_checks(self):
        """
        Checks if 'check_needed' is True for all nodes in the graph.
        For each node where 'check_needed' is True, the necessary checks are implemented.

        For complex relative clauses, it
        - removes the triple with the relative pronoun from self.triples,
        - updates the role of the specular, inverted triple to match the node's role, but keeping it inverted.
        """
        ##### relative clauses #####
        for node in self.nodes:
            if hasattr(node, 'check_needed') and node.check_needed:
                removed_triple = self.find_and_remove_from_triples(node.var_name, 2, return_value=True)

                if removed_triple:
                    for triple in self.triples:
                        if triple[1].endswith('-of') and triple[2] == removed_triple[0]:
                            new_role = node.role.split('-')[0] + '-of'
                            self.triples.append((triple[0], new_role, triple[2]))
                            self.triples.remove(triple)
                            break

    def to_penman(self):
        """
        Transform the nested dictionary obtained from UD into a Penman graph.
        First, delete 'instance' tuples if they are not associated with any roles,
        as well as other invalid triples (e.g. role is None).
        """
        self.remove_duplicate_triples()
        self.postprocessing_checks()
        self.triples = [tup for tup in self.triples if tup[1] != 'other']  # other is a temp label
        ignored_types = {'instance', 'refer-number', 'refer-person', 'aspect'}
        root = self.root_var or next((t[2] for t in self.triples if t[1] == 'root'), None)
        valid_third =  {tup[2] for tup in self.triples if tup[1] not in ignored_types}

        to_remove = []
        for i, tup in enumerate(self.triples):
            if not tup[1]:
                to_remove.append(tup[2])
            if tup[0] not in valid_third and tup[0] != self.root_var:
                to_remove.append(tup[0])

        self.triples = [tup for tup in self.triples if tup[0] not in to_remove and tup[2] not in to_remove]

        try:
            self.correct_variable_name()
            self.reorder_triples()
            g = penman.Graph(self.triples)
            return penman.encode(g, top=root, indent=4)

        except LayoutError as e:
            for n in self.triples:
                print(n)
            print(f"Skipping sentence due to LayoutError: {e}")

    def find_in_triples(self, variable, position):
        """
        Check if there is at least one triple in triples where the third element is equal to the given variable.

        Args:
            variable: the value to compare against the n element of each triple.
            position: the position (1, 2, 3) of the element to compare against.

        Returns:
        int: The index of the first triple with the specified element equal to the given variable,
             or -1 if no such element is found.
        """
        for i, triple in enumerate(self.triples):
            if variable == triple[position]:
                return i
        return -1

    def find_and_remove_from_triples(self, variable, position, return_value=False):
        """
        Find and remove the first triple in `self.triples` where the specified element matches the given variable
        at the specified position.

        Args:
            variable: The value to compare against the element of each triple.
            position: The position (0, 1, 2) of the element to compare against.
            return_value: If True, the matching triple is returned.
        """
        index = self.find_in_triples(variable, position)
        if index != -1:
            triple_to_return = self.triples[index]

            del self.triples[index]

            if return_value:
                return triple_to_return

    def find_and_replace_in_triples(self, variable_to_find, position, replacement, position_2):
        """
        Find and replace the first triple in `self.triples` where the specified element matches the given variable
        at the specified position.

        Args:
            variable_to_find: The value to compare against the element of each triple.
            position: The position (0, 1, 2) of the element to compare against.
            replacement: The value to replace the queried variable.
            position_2: The position (0, 1, 2) of the element to replace.
        """
        index = self.find_in_triples(variable_to_find, position)
        if index != -1:
            triple = list(self.triples[index])
            triple[position_2] = replacement
            self.triples[index] = tuple(triple)
