import re, sys
from collections import defaultdict
import penman
import warnings
from penman.exceptions import LayoutError

from umr_node import UMRNode, type_of_triple

def has_parent_attached(parent, stored_dependencies, root, visited=None):
    """ Checks whether a node is connected to another node, in order to identify disconnected ones.
    Returns the parent node if it is disconnected, else None.

    Args:
        parent (str): The current node being checked.
        stored_dependencies (dict): A dictionary representing the graph, where keys are nodes and values are sets of
        child nodes.
        root (str): The root node of the graph, representing the expected endpoint of a valid path.
        visited (set, optional): A set of nodes that have been visited during the traversal, used to detect cycles.
        Defaults to `None`.
    """
    if visited is None:
        visited = set()

    # if the parent is None, or the root has been reached, return None (no disconnection).
    if parent is None or parent == root:
        return None

    # if this node has already been visited, it is a cycle.
    if parent in visited:
        # raise ValueError(f"Cyclic dependency detected starting at {parent}")
        return None

    visited.add(parent)
    keys_with_child = [key for key, value_set in stored_dependencies.items() if parent in value_set]
    if not keys_with_child:
        return parent
    grandparent = keys_with_child[0]
    return has_parent_attached(grandparent, stored_dependencies, root, visited)


def reorder_triples(triples):
    """
    Reorders the list of triples stored based on a custom hierarchy for the role in each triple, to reflect a natural
    order of manual annotation.
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
            'mod': 13,
            'op1': 14,
            'op2': 15,
            'op3': 16,
            'op4': 17,
            'op5': 18,
            'refer-person': 19,
            'refer-number': 20,
            'modal-predicate': 21,
            'modal-strength': 22,
            'aspect': 23,
            'quot': 24
        }
        return hierarchy_order.get(role, float('inf'))

    return sorted(triples, key=lambda t: get_priority(t[1]))


class UMRGraph:
    def __init__(self, ud_tree, sent_num, deprels, language, vnaming, rel_roles, advcls, modality, conjunctions):
        """
        Initializes a UMRGraph instance to represent a sentence UMR graph.

        Attributes:
            ud_tree: The UD tree (Udapi Node).
            sent_num: The sentence number.
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
            vnaming (str): The naming convention for variable names, either 'first' or 'x'.
            rel_roles (set): lexical resource to disambiguate have-rel-role-92.
            advcls (dict): lexical resource to disambiguate adverbial clauses.
            modality (dict): lexical resource to disambiguate modal-strength and modal-predicate.
            conjunctions (dict): lexical resource to disambiguate coordinating conjunctions.
        """
        self.ud_tree = ud_tree
        self.sent_num = sent_num
        self.deprels = deprels
        self.root_var = None
        self.nodes: list[UMRNode] = []
        self.lang = language
        self.var_naming = vnaming
        self.triples = []
        self.track_conj = {}
        self.extra_level = {}  # node: new_umr_parent, e.g. {var of ARG1: var of roleset-91}
        self.rel_roles = rel_roles
        self.advcl =  advcls
        self.modals = modality
        self.conjs = conjunctions

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
        Assign a unique variable name based on the first letter of ud_node.lemma, if var_naming == 'first'. Else, 'x'.
        If a name is already taken, add a number suffix to make it unique.

        Args:
            form: The UD node with a 'lemma' attribute, or a string.

        Returns:
            str: A unique variable name.
        """
        lemma = form.lemma if hasattr(form, 'lemma') else form

        if self.var_naming == 'first':
            first_char = form.lemma[0].lower() if hasattr(form, 'lemma') else form[0].lower()
            first_char = first_char if first_char.isalpha() else 'x'
        else:  # self.var_naming == 'x'
            first_char = 'x'

        base_name = f"s{self.sent_num}{first_char}"
        count = 2

        # ensure uniqueness
        var_name = base_name
        while var_name in self.variable_names:
            var_name = f"{base_name}{count}"
            count += 1

        self.triples.append((var_name, 'instance', lemma))

        if not isinstance(form, str) and form.parent.is_root():
            self.root_var = var_name

        return var_name

    def correct_variable_name(self):
        """
        Return a list of triples with corrected variable naming, if necessary.
        Corrects variable names by organizing them by letter, ensuring sequential numbering.
        """
        var_pattern = re.compile(r"^([a-z])(\d+)([a-z])(\d*)$")

        var_groups = {}

        var_names = [v for v in self.variable_names if v == self.root_var or self.find_in_triples(v, 2) != -1]

        for var in var_names:
            match = var_pattern.match(var)
            if match:
                base_letter = match.group(3)
                number = int(match.group(4)) if match.group(4) else 1
                var_groups.setdefault(base_letter, []).append((number, var))

        renaming_map = {}

        for base_letter, variables in var_groups.items():
            variables.sort()

            for new_number, (current_number, var) in enumerate(variables, start=1):
                new_var = f"s{self.sent_num}{base_letter}{new_number if new_number > 1 else ''}"

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

        return corrected_triples, renaming_map.get(self.root_var, self.root_var)

    def remove_duplicate_triples(self):
        """ Removes duplicate triples from self.triples. """
        self.triples = list(set(self.triples))

    def remove_invalid_triples(self):
        """
        Removes from the graph triples:
        - with same parent and child, e.g. (A :role A),
        - where the parent is not a child in another triple, except for the root variable.
        """
        self.triples = [tup for tup in self.triples if tup[0] != tup[2]]
        self.triples = [tup for tup in self.triples if tup[1] and tup[1] not in ['other', 'root']]
        self.triples = [tup for tup in self.triples if tup[0]]

    def remove_invalid_variables(self):
        """ Iterates over the list of triples and checks if every variable has also an instance triple. """
        var_pattern = r's\d+[a-zA-Z]\d*'

        for tup in self.triples:
            if tup[1].startswith('op') and not re.fullmatch(var_pattern, tup[2]) or tup[1] in ['refer-person', 'refer-number', 'aspect', 'modal-strength', 'instance', 'quant', 'polarity', 'mode']:
                continue
            else:
                var = tup[2]

                # Check if there exists an instance triple for the given variable
                if not any(t for t in self.triples if t[0] == var and t[1] == 'instance'):
                    self.triples.remove(tup)

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

        ##### refer-number incorrectly assigned to NEs #####
        for triple in self.triples:
            if triple[1] == 'instance' and triple[2] == 'type-NE':
                corresponding_triple = next(
                    (t for t in self.triples if t[0] == triple[0] and t[1] == 'refer-number'),
                    None
                )
                if corresponding_triple:
                    self.triples.remove(corresponding_triple)

    def avoid_disconnection(self):
        dependencies = defaultdict(set)
        disconnecting = set()

        for tup in self.triples:
            par, ed, ch = tup
            if type_of_triple(tup) == 'relation':
                dependencies[par].add(ch)

        for tup in self.triples:
            par, ed, ch = tup
            res = has_parent_attached(par, dependencies, self.root_var)
            if res:
                disconnecting.add(res)

        for node in disconnecting:
            self.find_and_remove_from_triples(node, 0)
            self.remove_orphans(node, dependencies)

    def to_penman(self):
        """
        Transform the nested dictionary obtained from UD into a Penman graph.
        First, delete 'instance' tuples if they are not associated with any roles,
        as well as other invalid triples (e.g. role is None).
        """
        self.remove_duplicate_triples()
        self.remove_non_inverted_triples_if_duplicated()
        self.postprocessing_checks()
        self.remove_invalid_triples()
        self.remove_invalid_variables()
        self.avoid_disconnection()

        corrected_triples, root = self.correct_variable_name()
        triples = reorder_triples(corrected_triples)
        g = penman.Graph(triples)
        return g, root

    def remove_orphans(self, parent, stored_dependencies, visited=None):
        """
        Recursively removes nodes that are disconnected from the graph.

        Args:
            parent (str): The current node being checked.
            stored_dependencies (dict): A dictionary representing the graph, where keys are parent nodes and values are
            sets of child nodes.
            visited (set, optional): A set of nodes that have already been visited during the traversal, to prevent
            cycles. Defaults to `None`.
        """

        if visited is None:
            visited = set()
        if parent in visited:
            return
        visited.add(parent)

        for child in list(stored_dependencies.get(parent, [])):
            self.triples = [tup for tup in self.triples if tup[0] != child and tup[2] != child]
            self.remove_orphans(child, stored_dependencies, visited)

    def find_in_triples(self, variable, position):
        """
        Check if there is at least one triple in triples where the given variable is found at the given position.

        Args:
            variable: the value to compare against the n element of each triple.
            position: the position (1, 2, 3) of the element to compare against.

        Returns:
        int: The index of the first triple with the specified element equal to the given variable,
             or -1 if no such element is found.
        """
        for i, triple in enumerate(self.triples):
            if variable == triple[position] and triple[1] != 'instance':
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
        ignored_roles = ['other', 'refer-number', 'refer-person', 'aspect', 'instance', 'mode', 'modal-strength']

        for triple in self.triples:
            a, role, b = triple
            if role and role not in ignored_roles:
                if not role.endswith('-of'):
                    inverted_role = f"{role}-of"
                    inverted_triple = (b, inverted_role, a)
                    if inverted_triple in self.triples:
                        to_remove.add(triple)

        self.triples = [triple for triple in self.triples if triple not in to_remove]

    def alignments(self, umr, output_file=None):
        """
        Computes the alignment block based on UD tokens.
        Raises a warning if there are two UMR nodes aligned to the same token.
        """
        destination = output_file if output_file else sys.stdout
        alignments = {}

        def format_range(index_list):
            """ Formats a list of integers into a compact range representation of alignments. """
            index_list.sort()
            a_range = []
            start = index_list[0]
            end = start

            for num in index_list[1:]:
                if num == end + 1:
                    end = num
                else:
                    a_range.append(f"{start}-{end}" if start != end else f"{start}-{start}")
                    start = end = num

            a_range.append(f"{start}-{end}" if start != end else f"{start}-{start}")
            return ", ".join(a_range)

        for v in umr.variables():
            node = UMRNode.find_by_var_name(self, v)
            num_token = node.ord if node else 0
            aligned = [num_token]

            if not isinstance(node.ud_node, str) and node.ud_node:
                # Alignment of auxiliary verbs to the main verb
                auxs = [c.ord for c in node.ud_node.children if c.udeprel == 'aux']
                # Alignment of SCONJ marks to the main verb -- comment out next line not to align SCONJs
                sconjs = [c.ord for c in node.ud_node.children if c.udeprel == 'mark' and c.upos == 'SCONJ']
                # Alignment of adpositions and articles to the parent noun; # comment out next line not to align them
                adps = [c.ord for c in node.ud_node.children if c.udeprel == 'case' or
                        (c.feats['PronType'] == 'Art' and c.udeprel == 'det')]

                aligned.extend(auxs + sconjs + adps)
                if num_token == '0-0':
                    aligned.remove(num_token)

            alignments[v] = format_range(aligned)

        sorted_alignments = dict(sorted(alignments.items(), key=lambda item: int(item[1].split('-')[0])))
        for var, al in sorted_alignments.items():
            print(f'{var}: {al}', file=destination)

        # Check that two variables are not aligned to a same UD token
        non_zero_values = [value for value in alignments.values() if value != '0-0']
        seen_values = set()
        for value in non_zero_values:
            numbers = set([num for v in value.split(', ') for num in v.split('-')])
            for num in numbers:
                if num in seen_values:
                    result = [int(num) for v in alignments.values() for part in alignments[v].split(',') for num in part.split('-')]
                    dup = [v for v in alignments if num in result]
                    warning_message = (
                        f"[Warning] Two variables aligned to the same token: {dup} in sentence {self.ud_tree.address()}"
                    )
                    warnings.warn(warning_message)
                seen_values.add(num)


