import re
import penman
from penman.exceptions import LayoutError
from sympy.logic.inference import valid

from umr_node import UMRNode


class UMRGraph:
    def __init__(self, ud_tree, deprels):
        """
        Initialize a UMRGraph for a sentence, mainly with:
        - a dictionary mapping UD deprels to UMR roles,
        - a root variable,
        - a list of nodes that are part of the graph,
        - a dictionary to store variable mappings and prepare to add nodes,
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

    def display_text(self):
        """Print out the text of the sentence."""
        print(f"SNT: {self.ud_tree.text}")

    def get_nodes(self):   # TODO:decidere se la voglio tenere
        """Method to collect nodes dynamically"""
        return [node for node in self.nodes]

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

        if first_letter in self.var_node_mapping:
            while f"{first_letter}{count}" in self.var_node_mapping:
                count += 1

        var_name = first_letter if first_letter not in self.var_node_mapping else f"{first_letter}{count}"
        self.var_node_mapping[var_name] = form
        lemma = form.lemma if hasattr(form, 'lemma') else form
        self.triples.append((var_name, 'instance', lemma))

        if not isinstance(form, str) and form.parent.is_root():
            self.root_var = var_name

        return var_name

    def correct_variable_name(self):
        """ Return a list of triples with corrected variable naming, if necessary. """

        var_pattern = re.compile(r"^([a-z])(\d*)$")
        var_groups = {}

        for var in self.var_node_mapping.keys():
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
                    self.var_node_mapping[new_var] = self.var_node_mapping.pop(var)

        corrected_triples = [
            (renaming_map.get(var, var), relation, renaming_map.get(value, value))
            for var, relation, value in self.triples
        ]

        return corrected_triples

    def to_penman(self):
        """
        Transform the nested dictionary obtained from UD into a Penman graph.
        First, delete 'instance' tuples if they are not associated with any roles,
        as well as other invalid triples (e.g. role is None).
        """
        ignored_types = {'instance', 'other', 'refer-number', 'refer-person', 'aspect'}
        root = self.root_var or next((t[2] for t in self.triples if t[1] == 'root'), None)
        valid_third =  {tup[2] for tup in self.triples if tup[1] not in ignored_types}

        to_remove = []
        for i, tup in enumerate(self.triples):
            if not tup[1]:
                to_remove.append(tup[2])
            if tup[1] in ['other']:
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
        Check if there is at least one triple in triples where the third element iis equal to the given variable.

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

