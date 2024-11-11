import re
import penman
from penman.exceptions import LayoutError
from umr_node import UMRNode


class UMRGraph:
    def __init__(self, ud_tree, deprels):
        """
        Initialize a UMRGraph for a sentence, mainly with:
        - a dictionary mapping UD deprels to UMR roles,
        - a root variable,
        - a list of nodes that are part of the graph,
        - a list to store all triples that will compose the graph.

        Args:
            ud_tree: The UD tree as from Udapi.
        """
        self.ud_tree = ud_tree
        self.deprels = deprels
        self.root_var = None
        self.nodes: list[UMRNode] = []
        self.var_node_mapping = {}
        self.triples = []
        self.track_conj = {}
        self.extra_level = {}  # node: new_umr_parent, e.g. {var of ARG1: var of roleset-91}

    def __repr__(self):
        return f"Sentence(Text: '{self.ud_tree.text}', nodes={self.nodes})"

    @property
    def variable_names(self):
        """
        A property that collects the 'var_name' attribute from all nodes in the graph.

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

    def postprocessing_checks(self):
        """
        Checks if 'check_needed' is True for all nodes in the graph.
        For each node where 'check_needed' is True, the necessary checks are implemented.

        For complex relative clauses, it
        - removes the triple with the relative pronoun from self.triples,
        - updates the role of the specular, inverted triple to match the node's role, but keeping it inverted.
        """

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
            g = penman.Graph(self.triples)
            return penman.encode(g, top=root, indent=4)

        except LayoutError as e:
            print(self.triples)
            print(f"Skipping sentence due to LayoutError: {e}")

    def find_node_by_role(self, role: str) -> list[UMRNode]:  # TODO: think if I want to keep it
        """Find and return nodes by their role."""
        return [node for node in self.nodes if node.role == role]

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
            del self.triples[index]

            if return_value:
                return self.triples[index]

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


