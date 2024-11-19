import re
import penman
import warnings
from penman.exceptions import LayoutError
from umr_node import UMRNode

class UMRGraph:
    def __init__(self, ud_tree, deprels, language):
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
        self.lang = language
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

        var_names = [v for v in self.variable_names if v == self.root_var or self.find_in_triples(v, 2) != -1]

        for var in var_names:
            match = var_pattern.match(var)
            if match:
                base_letter = match.group(1)
                number = int(match.group(2)) if match.group(2) else 1
                var_groups.setdefault(base_letter, []).append((number, var))

        renaming_map = {}

        for base_letter, variables in var_groups.items():
            variables.sort()

            for new_number, (current_number, var) in enumerate(variables, start=1):
                new_var = f"{base_letter}{new_number if new_number > 1 else ''}"

                if new_var != var:
                    renaming_map[var] = new_var
                    to_replace = UMRNode.find_by_var_name(self, new_var)
                    if to_replace:
                        to_replace.var_name = None
                    to_rename = UMRNode.find_by_var_name(self, var)
                    to_rename.var_name = new_var

        corrected_triples = [
            (renaming_map.get(var, var), relation, renaming_map.get(value, value))
            for var, relation, value in self.triples
        ]

        self.triples = corrected_triples

        return renaming_map.get(self.root_var, self.root_var)

    def remove_duplicate_triples(self):
        """ Removes duplicate triples from self.triples. """
        self.triples = list(set(self.triples))

    def reorder_triples(self):
        """
        Reorders the list of triples stored in `self.triples` based on a predefined hierarchy for the
        role (second element) in each triple, to reflect a natural order of manual annotation.
        Main features:
        - triples are grouped based on their first node (triple[0]) to facilitate handling nested dependencies.
        - a recursive function ensures that child nodes are added after their parent.
        - each group of triples for a given node is sorted based on the predefined get_priority function.
        """
        hierarchy_order = {
            'instance': 0,
            'actor': 1,
            'undergoer': 2,
            'theme': 3,
            'ARG1': 4,
            'ARG2': 5,
            'affectee': 6,
            'OBLIQUE': 7,
            'refer-person': 8,
            'refer-number': 9,
        }

        def get_priority(triple):
            role = triple[1]

            if role == 'quot':
                return 20
            elif role == 'aspect':
                return 21
            elif role == 'modal-strength':
                return 22

            if role.startswith('op'):
                try:
                    op_number = int(role[2:])
                    return 11 + op_number
                except ValueError:
                    return 12

            return hierarchy_order.get(role, 18)

        visited_nodes = set()
        reordered_triples = []

        def add_triples(node):
            if node in visited_nodes:
                return
            visited_nodes.add(node)

            for triple in grouped_triples.get(node, []):
                if triple not in reordered_triples:
                    reordered_triples.append(triple)
                    add_triples(triple[2])  # Recurse on the child node

        # Step 1: Group triples by their source node
        grouped_triples = {}
        for tup in self.triples:
            source = tup[0]
            grouped_triples.setdefault(source, []).append(tup)

        # Step 2: Process triples starting from the root node(s)
        for tup in self.triples:
            if tup[0] not in visited_nodes:
                add_triples(tup[0])

        # Step 3: Sort the triples based on their priorities
        self.triples = sorted(reordered_triples, key=get_priority)

        # Post-processing: make sure that 'quot' is not listed too early, in order to avoid the Penman library to
        # reverse the relation automatically (quot-of).
        self.triples = [t for t in self.triples if t[1] != 'quot'] + [t for t in self.triples if t[1] == 'quot']

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
                        if triple[1] and triple[1].endswith('-of') and triple[2] == removed_triple[0]:
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
        self.remove_non_inverted_triples_if_duplicated()
        # self.postprocessing_checks()
        self.triples = [tup for tup in self.triples if tup[1] not in ['other', 'root']]  # other is a temp label
        ignored_types = {'instance', 'refer-number', 'refer-person', 'aspect'}
        valid_third =  {tup[2] for tup in self.triples if tup[1] not in ignored_types}
        inverted_third = {tup[0] for tup in self.triples if tup[1] and tup[1].endswith('-of') and tup[1] not in ignored_types}
        valid_third = valid_third | inverted_third

        to_remove = []
        for i, tup in enumerate(self.triples):
            if not tup[1]:
                to_remove.append(tup[2])
            if tup[0] not in valid_third and tup[0] != self.root_var:
                to_remove.append(tup[0])

        self.triples = [tup for tup in self.triples if tup[0] not in to_remove and tup[2] not in to_remove]

        try:
            root = self.correct_variable_name()
            self.reorder_triples()
            g = penman.Graph(self.triples)
            return penman.encode(g, top=root, indent=4)

        except LayoutError as e:
            # for n in self.triples:
            #     print(n)
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
        Find and replace all triples in `self.triples` where the specified element matches
        the given variable at the specified position.

        Args:
            variable_to_find: The value to compare against the element of each triple.
            position: The position (0, 1, 2) of the element to compare against.
            replacement: The value to replace the queried variable.
            position_2: The position (0, 1, 2) of the element to replace.
        """
        called = False
        for i, triple in enumerate(self.triples):
            if triple[position] == variable_to_find:
                called=True
                modified_triple = list(triple)
                modified_triple[position_2] = replacement
                self.triples[i] = tuple(modified_triple)

        return called

    def remove_non_inverted_triples_if_duplicated(self):
        """
        Modifies self.triples by removing any non-inverted triples that have a corresponding inverted version.
        A pair is defined as (a, role, b) and (b, role-of, a), where the non-inverted triple (a, role, b) is removed.
        """
        to_remove = set()
        ignored_roles = ['other', 'refer-number', 'refer-person', 'aspect', 'instance']

        for triple in self.triples:
            a, role, b = triple
            if role and role not in ignored_roles:
                if not role.endswith('-of'):
                    inverted_role = f"{role}-of"
                    inverted_triple = (b, inverted_role, a)
                    if inverted_triple in self.triples:
                        to_remove.add(triple)

        self.triples = [triple for triple in self.triples if triple not in to_remove]

    def alignments(self):
        """
        Computes alignment block based on UD tokens.
        Raises a warning if there are two UMR nodes aligned to the same token.
        """
        variables = {triple[0] for triple in self.triples if triple[1] == 'instance'}
        alignments = {}

        for v in variables:
            node = UMRNode.find_by_var_name(self, v)
            num_token = node.ud_node.ord if hasattr(node.ud_node, 'ord') else 0
            alignments[v] = num_token
            print(f'{v}: {num_token}-{num_token}')

        # Check that two variables are not aligned to a same UD token
        non_zero_values = [value for value in alignments.values() if value != 0]
        seen_values = set()

        for value in non_zero_values:
            if value in seen_values:
                dup = [v for v in alignments if alignments[v] == value]
                warning_message = (
                    f"[Warning] Two variables aligned to the same token: {dup} in sentence {self.ud_tree.address()}"
                )
                warnings.warn(warning_message)
            seen_values.add(value)


