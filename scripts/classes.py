from typing import List, Dict, Union, Optional

class UMRNode:
    def __init__(self, ud_node, tree, role: str = "", properties: Dict[str, Union[str, int, bool]] = None):
        """
        Initialize a Node with a token's text, role, and additional properties.

        Args:
            ud_node: UD node from Udapi.
            tree (UDTree): The UDTree instance to which this Node belongs.
            role (str): role of the token within the sentence or graph (e.g., actor).
            properties (dict): additional attributes of the token.
        """
        self.node = ud_node
        self.token_text = ud_node.lemma
        self.tree = tree
        self.role = role
        self.properties = properties if properties else {}
        self.var_name = self.tree.get_variable_name(ud_node)

    def __repr__(self):
        return f"Node(token_text='{self.token_text}', role='{self.role}', properties={self.properties})"

    def add_property(self, key: str, value: Union[str, int, bool]):
        """Add or update a property for the node."""
        self.properties[key] = value

    def get_property(self, key: str):
        """Get a property value by key, returning None if not found."""
        return self.properties.get(key)


class UDTree:
    def __init__(self, tree):
        """
        Initialize a UDTree (sentence) with a raw text and a dictionary to store variable mappings and prepare to add nodes.

        Args:
            tree: The raw text of the sentence.
        """
        self.tree = tree
        self.nodes: List[UMRNode] = []
        self.var_node_mapping = {}
        self.deprels = {}    # maybe not

    def get_variable_name(self, ud_node):
        """
        Assigns a unique variable name based on the first letter of ud_node.lemma.
        If a name is already taken, add a number suffix to make it unique.

        Args:
            ud_node: The UD node with a 'lemma' attribute.

        Returns:
            str: A unique variable name.
        """
        first_letter = ud_node.lemma[0].lower()
        count = 2

        if first_letter in self.var_node_mapping:
            while f"{first_letter}{count}" in self.var_node_mapping:
                count += 1

        var_name = first_letter if first_letter not in self.var_node_mapping else f"{first_letter}{count}"
        self.var_node_mapping[var_name] = ud_node

        return var_name

    def add_node(self, ud_node, tree, role: str = "", properties: Dict[str, Union[str, int, bool]] = None):
        """Create a new node and add it to the sentence."""
        node = UMRNode(ud_node, tree, role=role, properties=properties)  # tree will be computed, not given
        self.nodes.append(node)

    def find_node_by_role(self, role: str) -> List[UMRNode]:
        """Find and return nodes by their role."""
        return [node for node in self.nodes if node.role == role]

    def display_text(self):
        """Print out the text of the sentence."""
        print(f"SNT: {self.tree.text}")

    def __repr__(self):
        return f"Sentence(Text: '{self.tree.text}', nodes={self.nodes})"