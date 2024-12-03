import re, sys
import penman
import warnings
from penman.exceptions import LayoutError
from umr_node import UMRNode

class UMRGraph:
    def __init__(self, ud_tree, deprels, language, rel_roles, advcls, modality):
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
            language (str): The langauge of the tree.
            rel_roles (set): lexical resource to disambiguate have-rel-role-92.
            advcls (dict): lexical resource to disambiguate adverbial clauses.
            modality (dict): lexical resource to disambiguate modal-strength and modal-predicate.
        """
        self.ud_tree = ud_tree
        self.deprels = deprels
        self.root_var = None
        self.nodes: list[UMRNode] = []
        self.lang = language
        self.triples = []
        self.track_conj = {}
        self.extra_level = {}  # node: new_umr_parent, e.g. {var of ARG1: var of roleset-91}
        self.rel_roles = rel_roles
        self.advcl =  advcls
        self.modals = modality

    def __repr__(self):
        return f"Sentence(Text: '{self.ud_tree.text}', nodes={self.nodes})"

    @property
    def variable_names(self):
        """
        Returns a list of 'var_name' values from each node in self.nodes.
        """
        return [node.var_name for node in self.nodes if hasattr(node, 'var_name')]

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

    def remove_invalid_triples(self):
        """ Removes invalid triples with same parent and child (e.g. A :role A). """
        self.triples = [tup for tup in self.triples if tup[0] != tup[2]]

    def remove_disconnecting_triples(self):
        """
        Removes triples from the graph where the parent (first element)
        is not a child in another triple, except for the root variable.
        """
        self.triples = [tup for tup in self.triples if tup[1] not in ['other', 'root']]  # other is a temp label

        ignored_types = {'instance', 'refer-number', 'refer-person', 'aspect', 'mode', 'modal-predicate', 'modal-strength'}
        valid_third = {tup[2] for tup in self.triples if tup[1] not in ignored_types} | {self.root_var}
        inverted_third = {tup[0] for tup in self.triples if tup[1] and tup[1].endswith('-of') and tup[1] not in ignored_types}
        valid_third = valid_third | inverted_third

        to_remove = {tup[2] for tup in self.triples if not tup[1]}
        to_remove.update(tup[0] for tup in self.triples if tup[0] not in valid_third)
        self.triples = [tup for tup in self.triples if tup[0] not in to_remove and tup[2] not in to_remove]

    def reorder_triples(self):
        """
        Reorders the list of triples stored in `self.triples` based on a custom hierarchy for the role in each
        triple, to reflect a natural order of manual annotation.
        """
        def get_priority(role):

            hierarchy_order = {
                'instance': 0,
                'actor': 1,
                'experiencer': 2,
                'undergoer': 3,
                'theme': 4,
                'stimulus': 5,
                'ARG1': 6,
                'ARG2': 7,
                'ARG3': 8,
                'ARG4': 9,
                'affectee': 10,
                'OBLIQUE': 11,
                'manner': 12,
                'op1': 13,
                'op2': 14,
                'op3': 15,
                'op4': 16,
                'op5': 17,
                'refer-person': 18,
                'refer-number': 19,
                'modal-predicate': 20,
                'modal-strength': 21,
                'aspect': 22,
                'quot': 23
            }
            return hierarchy_order.get(role, float('inf'))

        self.triples = sorted(self.triples, key=lambda t: get_priority(t[1]))

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
                    for rt in removed_triple:
                        for triple in self.triples:
                            if triple[1] and triple[1].endswith('-of') and triple[2] == rt[0]:
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
        self.remove_invalid_triples()
        self.postprocessing_checks()
        self.remove_disconnecting_triples()
        root = self.correct_variable_name()
        self.reorder_triples()

        try:
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
        Find and remove all triples in `self.triples` where the specified element matches the given variable
        at the specified position.

        Args:
            variable: The value to compare against the element of each triple.
            position: The position (0, 1, 2) of the element to compare against.
            return_value: If True, the matching triples are returned as a list.
        """
        matching_triples = [triple for triple in self.triples if triple[position] == variable]

        self.triples = [triple for triple in self.triples if triple[position] != variable]

        if return_value:
            return matching_triples

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

    def alignments(self, output_file=None):
        """
        Computes alignment block based on UD tokens.
        Raises a warning if there are two UMR nodes aligned to the same token.
        """
        destination = output_file if output_file else sys.stdout

        variables = {triple[0] for triple in self.triples if triple[1] == 'instance'}
        alignments = {}

        for v in variables:
            node = UMRNode.find_by_var_name(self, v)
            num_token = node.ud_node.ord if hasattr(node.ud_node, 'ord') else 0
            alignments[v] = num_token
            print(f'{v}: {num_token}-{num_token}', file=destination)

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


