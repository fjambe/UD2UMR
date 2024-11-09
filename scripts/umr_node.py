from penman.models.amr import model as pm
from preprocess import interpersonal, advcl


class UMRNode:
    def __init__(self, ud_node, umr_graph, role: str = ""):
        """
        Initialize a Node with the corresponding Udapi node and its associated role.

        Args:
            ud_node: UD node from Udapi, if available, else a string.
            umr_graph (UMRGraph): The UMRGraph instance to which this Node belongs.
            role (str): role of the token within the sentence or graph (e.g., actor).
        """
        self.ud_node = ud_node
        self.umr_graph = umr_graph
        self.role = role
        self.var_name = self.umr_graph.assign_variable_name(ud_node)
        self.parent_var_name = None
        self.already_added = False
        self.called_pron = False
        self.called_quantifiers = False
        self.called_possessives = False
        self.called_det_pro_noun = False


    def __repr__(self):
        return f"Node(token='{self.ud_node.form if not isinstance(self.ud_node, str) else self.ud_node}', role='{self.role}', var_name='{self.var_name})"


    def find_parent(self, query_node):
        """ Find the variable associated to the parent node. """

        var_parent = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == query_node), None)
        if query_node == self.ud_node.parent:
            self.parent_var_name = var_parent

        return var_parent, query_node.is_root()

    def introduce_abstract_roleset(self, role_aka_concept):
        """ Build an instance of abstract roleset (e.g., identity-91). """

        # TODO: it should also work for reification in general, so it could be renamed. Decide later.
        # double check also that role inversion can be generalized.

        var_parent = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == self.ud_node.parent), None)  # modify for sure
        triples = [tup for tup in self.umr_graph.triples if tup[1] != role_aka_concept]
        var_concept = self.umr_graph.assign_variable_name(role_aka_concept)
        triples.extend([
            (var_concept, 'instance', role_aka_concept),
            pm.invert((var_concept, 'ARG1', var_parent)),
            (var_concept, 'ARG2', self.var_name),
            (var_concept, 'aspect', 'state')
        ])

    def replace_with_abstract_roleset(self, role_aka_concept, replace_arg=None, overt=True):
        """
        Replace a syntactic construction with a UMR abstract roleset.
        extra_level: dictionary keeping track of nodes that have changed parent (syntactic vs. semantic) due to the
        introduction of an abstract roleset.
        overt: whether the predication is explicit (relates to copulas, with or without verb 'to be')
        """

        # TODO: Figure out whether it can be merged with introduce_abstract_roleset().

        second_arg = 'ARG2' if not replace_arg else replace_arg
        root_var = None

        var_parent = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == self.ud_node.parent), None)  # cambiare sicuro TODO, dopo aver creato i nuovi nodi
        var_sum = self.var_name if overt else None
        triples = [tup for tup in self.umr_graph.triples if var_sum != tup[2]]

        var_concept, var_node_mapping = self.umr_graph.assign_variable_name(role_aka_concept)

        nsubj = next((s for s in self.ud_node.siblings if s.deprel == 'nsubj'), None)
        if overt:
            var_nsubj = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == nsubj), None)
        else:
            var_nsubj = self.var_name

        self.umr_graph.extra_level[var_parent] = var_concept
        self.umr_graph.extra_level[var_nsubj] = False

        for i, tup in enumerate(self.umr_graph.triples):
            # reassigning root, if relevant
            if tup[2] == var_parent and tup[1] == 'root':
                root_var = var_concept
                self.umr_graph.triples[i] = (tup[0], tup[1], var_concept)
            if tup[2] == var_parent and tup[1] == 'ARG2':
                triples[i] = (tup[0], tup[1], var_concept)
            # reassigning nsubj (previously actor)
            elif tup[2] == var_nsubj and tup[1] == 'actor':
                self.umr_graph.triples[i] = (var_concept, 'ARG1', tup[2])

        if var_nsubj not in [t[2] for t in triples] and not overt:
            self.umr_graph.triples.append((var_concept, 'ARG1', var_nsubj))

        self.umr_graph.triples = [tup for tup in triples if tup[2] != var_parent]  # remove old role
        self.umr_graph.triples.extend([
            (var_concept, second_arg, var_parent),
            (var_concept, 'aspect', 'state')
        ])

        # reattach non-core (+ obl:arg) dependents of UD root to UMR abstract predicate
        for n in self.ud_node.siblings:
            if n.udeprel in ['vocative', 'obl', 'advmod', 'discourse', 'advmod']:
                var_n = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == n), None)
                if var_n:
                    self.umr_graph.triples = [(var_concept, tup[1], tup[2]) if tup[2] == var_n else tup for tup in self.umr_graph.triples]

        # elided subjects to be restored
        rel_dep = [s for s in self.ud_node.siblings if s.deprel == 'acl:relcl']
        if overt and nsubj is None and not rel_dep:
            arg_type = 'person' if self.ud_node.feats['Person'] in ['1', '2'] else 'FILL'
            new_node = self.create_node(arg_type)
            self.umr_graph.triples.append((var_concept, 'ARG1', new_node.var_name))

        return root_var

    def add_node(self,
                 role,
                 invert: bool = False,
                 def_parent=None):
        """
        Create and add a new node. Steps:
        2. If the node is the root, its variable name is returned;
        3. Link the var_name to its parent node via their relation ('role'), if the node is not the root.
        """

        parent = def_parent or self.find_parent(self.ud_node.parent)[0]

        if not invert:
            self.umr_graph.triples.append((parent, role, self.var_name))
        else:
            self.umr_graph.triples.append(pm.invert((self.var_name, role, def_parent)))

    def ud_to_umr(self):
        """ Map UD information to UMR structures. """

        root_var = None

        if self.ud_node.deprel == 'root':
            self.add_node(self.role)
            self.umr_graph.root_var = self.var_name
            self.already_added = True

        ### checking UPOS ###
        if self.ud_node.upos == 'PRON':
            self.personal()

            # TODO: do something with non-personal pronouns, here.
            if self.called_pron:
                self.already_added = True

        elif (self.ud_node.upos == 'NOUN' and self.role != 'other') or (
                self.ud_node.upos == 'ADJ' and self.ud_node.deprel in ['nsubj', 'obj', 'obl']):
            self.add_node(self.role)
            self.umr_graph.triples.append(self.get_number_person('number'))
            self.already_added = True

        elif self.ud_node.upos == 'DET':
            # check for PronType=Prs is inside the function
            self.possessives()
            # now check for quantifiers (PronType=Tot)
            self.quantifiers(self.role if self.role != 'det' else 'quant')

            # check if they substitute for nouns
            self.det_pro_noun()
            if self.called_possessives or self.called_quantifiers or self.called_det_pro_noun:
                self.already_added = True

            elif self.ud_node.deprel == 'det':
                self.add_node('mod')
                self.already_added = True

        elif self.ud_node.upos == 'VERB':
            # elided subjects to be restored
            if 'nsubj' not in [d.udeprel for d in
                               self.ud_node.children] and self.ud_node.parent.deprel != 'root':  # root check is a bit random
                if self.ud_node.feats['Voice'] != 'Pass':
                    arg_type = 'person' if self.ud_node.feats['Person'] in ['1', '2'] else 'FILL'
                    new_node = self.create_node(arg_type)
                    parent, _ = self.find_parent(self.ud_node)
                    self.umr_graph.triples.append((parent, 'actor', new_node.var_name))

        ### checking deprel ###
        if self.ud_node.deprel == 'conj':
            role = next((k for k, v in self.umr_graph.deprels.items() for item in v if item == self.ud_node.parent), None)
            already_added, root_var = self.coordination(role)
        elif self.ud_node.deprel == 'appos':
            self.introduce_abstract_roleset(self.role)
            self.already_added = True

        elif self.ud_node.deprel == 'cop':
            root_var = self.copulas()
            self.already_added = True

        # copular constructions with no overt copula
        elif self.ud_node.deprel == 'nsubj' and self.ud_node.parent.upos != 'VERB' and not [s for s in self.ud_node.siblings if
                                                                            s.deprel == 'cop']:
            root_var = self.copulas(copula=False)
            self.already_added = True

        elif self.ud_node.deprel == 'acl:relcl':
            rel_pron = next((d for d in self.ud_node.descendants if d.feats.get('PronType') == 'Rel'), None)
            if not rel_pron:
                if self.ud_node.parent.feats.get('PronType') == 'Rel':
                    rel_pron = self.ud_node.parent
                else:
                    rel_pron = next((d for d in self.ud_node.descendants if d.upos == 'ADV'), None)

            role = next((k for k, v in self.umr_graph.deprels.items() if rel_pron in v), None)

            self.relative_clauses(rel_pron, role)
            self.already_added = True
            # already_added.add(rel_pron) # TODO - FIX

        elif self.ud_node.deprel == 'advcl':
            self.adverbial_clauses()
            self.already_added = True

        if not self.already_added:
            self.add_node(self.role)
            self.already_added = True

        self.umr_graph.root_var = root_var if root_var else self.umr_graph.root_var

    ####################### Language checks ##########################

    def personal(self):
        """ Handle personal pronouns. """

        # TODO: could probably be expanded to handle all pronouns.
        if self.ud_node.feats['PronType'] == 'Prs':
            self.called_pron = True

            pron = self.create_node('person' if self.ud_node.feats['Gender'] != 'Neut' else 'thing', replace=True)

            parent, _ = self.find_parent(self.ud_node.parent)
            self.umr_graph.triples.append((parent, self.role, pron.var_name))

    def create_node(self,
                    category: str,
                    replace: bool = False,
                    reflex: bool = False):
        """
        Create a new node, whose type is decided based on 'category'. Allowed 'category' values: ['person','thing', 'FILL'].
        FILL is used when it is not easy to automatically detect if the new node should be person or thing.
        If True, the 'replace' parameter deletes an existing node, which is then replaced by the newly created one
        (e.g. the case of personal pronouns).
        If False (default), a new node is inserted without any being replaced.
        """

        new_node = UMRNode(category, self.umr_graph)

        if replace:
            del self.umr_graph.var_node_mapping[self.var_name]
            triples = [x for x in self.umr_graph.triples if x[0] != self.var_name]
            for i, tup in enumerate(triples):
                triples[i] = tuple(new_node.var_name if el == self.var_name else el for el in tup)  # remove old rel

            self.umr_graph.var_node_mapping[new_node.var_name] = self.ud_node

        if category == 'person':
            self.umr_graph.triples.append(self.get_number_person('person', new_node.var_name))

        if not reflex:
            self.umr_graph.triples.append(self.get_number_person('number', new_node.var_name))

        return new_node

    def get_number_person(self,
                          feature: str,
                          new_var_name: str = None):
        """ Extract refer-number and refer-person attributes. """

        feats = {
            **{k: '3rd' for k in ['3', 'ille', 'hic', 'is', 'ipse']},
            'Sing': 'singular',
            'Plur': 'plural',
            '1': '1st',
            '2': '2nd',
        }

        var_name = new_var_name if new_var_name else self.var_name
        feat = feats.get(
            self.ud_node.feats.get(f"{feature.capitalize()}[psor]") or self.ud_node.feats.get(feature.capitalize()) or self.ud_node.lemma,
            'FILL')

        return var_name, f'refer-{feature}', feat

    def possessives(self):
        """
        Handle possessive constructions.
        1. Basic case: possessive adjectives
        2. Non-reflexive 3rd person (eius): TODO
        3. General possession: encoded by the deprel nmod:poss, not treated here. Otherwise undetectable, because lexical.
        """

        numbers = {'Sing': 'singular', 'Plur': 'plural'}

        if self.ud_node.feats['PronType'] == 'Prs':
            self.called_possessives = True
            is_adj_noun = self.ud_node.parent.upos in ['ADJ', 'NOUN', 'PROPN'] or [c for c in self.ud_node.children if c.deprel == 'cop']
            is_reflexive = self.ud_node.lemma == 'suus'
            parent, _ = self.find_parent(self.ud_node.parent)

            base_type = 'person' if is_adj_noun else ('thing' if self.ud_node.parent.upos == 'VERB' and self.ud_node.feats['Gender'] == 'Neut' else 'FILL')
            poss = self.create_node(base_type, replace=is_adj_noun, reflex=is_reflexive)

            self.umr_graph.triples.append((parent, 'poss' if is_adj_noun else self.role, poss.var_name))

            if is_reflexive:
                refer_number = numbers.get(self.ud_node.feats['Number'] if not is_adj_noun else self.ud_node.parent.parent.feats['Number'])
                self.umr_graph.triples.append((self.var_name, 'refer-number', refer_number))

            # attaching the possessive itself
            if self.ud_node.parent.upos == 'VERB':
                poss = self.create_node('person', replace=True, reflex=is_reflexive)
                self.umr_graph.triples.append((self.var_name, 'poss', poss.var_name))
                if is_reflexive:
                    self.umr_graph.triples.append((poss.var_name, 'refer-number', numbers.get(self.ud_node.parent.feats['Number'])))


    def quantifiers(self, role):
        """ Handle quantifiers. """

        if self.ud_node.feats['PronType'] == 'Tot':

            cop_siblings = [s for s in self.ud_node.siblings if s.deprel == 'cop']
            has_cop_sibling = len(cop_siblings) > 0

            if self.ud_node.deprel == 'det' and not has_cop_sibling:
                self.called_quantifiers = True
                self.add_node(role)

            elif self.ud_node.deprel != 'det' or (self.ud_node.deprel == 'det' and len(cop_siblings) == 1):
                self.called_quantifiers = True
                new_node = self.create_node('thing' if self.ud_node.feats['Gender'] == 'Neut' else 'FILL')

                parent, _ = self.find_parent(self.ud_node.parent)
                self.umr_graph.triples.append((parent, self.role, new_node.var_name))
                self.umr_graph.var_node_mapping[new_node.var_name] = self.ud_node

                # attaching the quantifier itself
                self.add_node('quant', def_parent=new_node.var_name)

    def det_pro_noun(self):
        """ Create an entity node that replaces the DETs (e.g. 'Illi negarunt' "They denied"). """

        if self.ud_node.deprel not in ['det', 'root'] or self.ud_node.feats['PronType'] == 'Dem':

            self.called_det_pro_noun = True
            type_arg = 'thing' if self.ud_node.feats['Gender'] == 'Neut' else 'person'  # maybe FILL is better

            new_node = self.create_node(type_arg, replace=True)
            parent, _ = self.find_parent(self.ud_node.parent)
            self.umr_graph.triples.append((parent, self.role, new_node.var_name))


    def coordination(self, role):
        """ Handle coordination by building the corresponding UMR structures. """

        conjs = {'or': ['vel', 'uel', 'aut'],
                 'and': ['que', 'et', 'ac', 'atque', 'nec', 'neque', ','],
                 'but-91': ['sed', 'at']}

        root_var = None

        # create one top node for the conjunction governing the coordination
        if self.ud_node.parent not in self.umr_graph.track_conj:  # node.parent is the head conjunct
            # identify conjunction type (polysyndeton or asyndeton)
            cc = next((c for c in self.ud_node.children if c.deprel == 'cc'), None)
            if cc is None:
                cc = next((c for c in self.ud_node.children if c.deprel == 'punct' and c.lemma == ','), None)
            cord = next((k for k, v in conjs.items() if cc and cc.lemma in v), None)
            var_node_mapping = {k: v for k, v in self.umr_graph.var_node_mapping.items() if
                                v != cc}  # remove cc for correct variable naming
            if not cord:  # coordination without conjunction/comma
                cord = 'and'
            if cc:
                self.umr_graph.triples = [tup for tup in self.umr_graph.triples if tup[2] != cc.lemma]
            var_name_conj = self.umr_graph.assign_variable_name(cord)
            self.umr_graph.triples.append((var_name_conj, 'instance', cord))

            # create variables for first two conjuncts, to set up the coordination structure
            # node.parent: 1st conjunct (true deprel), node: 2nd conjunct (deprel = conj, #1)
            var_node_mapping = dict(reversed(var_node_mapping.items()))  # so that artificial nodes have precedence
            # have to handle abstract predicates - there's probably a smarter way to do this
            var_first_conj = next((k for k, v in var_node_mapping.items() if v == self.ud_node.parent), None)
            var_second_conj = next((k for k, v in var_node_mapping.items() if v == self.ud_node), None)

            role = role
            parent, new_root = self.find_parent(self.ud_node.parent.parent)
            for tup in self.umr_graph.triples:  # avoid clashes of abstract concepts and coordination
                if tup[2] == var_first_conj:
                    if var_first_conj in self.umr_graph.extra_level and self.ud_node.parent.deprel == 'root':
                        root_var = var_name_conj
                        break
                    role, parent = tup[1], tup[0]
                    break

            triples = [tup for tup in self.umr_graph.triples if not (tup[0] == parent and tup[1] == role)]
            triples.append((parent, role, var_name_conj))
            self.umr_graph.track_conj[self.ud_node.parent] = var_name_conj

            # Attach first and second conjuncts to the conjunction node
            if var_first_conj not in self.umr_graph.extra_level:  # TODO fare un check a tappeto che non abbia sputtanato tutto
                triples = [tup for tup in triples if
                           not (tup[2] == var_first_conj and tup[1] != 'instance')]  # remove previous relation, if any
            arg_type = 'op' if cord != 'but-91' else 'ARG'

            for i, vc in enumerate([var_first_conj, var_second_conj], start=1):
                if not self.umr_graph.extra_level.get(vc, None):
                    triples.append((var_name_conj, f'{arg_type}{i}', vc))
                else:
                    triples.append((var_name_conj, f'{arg_type}{i}', self.umr_graph.extra_level[vc]))

            if (self.ud_node.upos == 'NOUN' and role != 'other') or (
                    self.ud_node.upos == 'ADJ' and self.ud_node.deprel in ['nsubj', 'obj', 'obl']):
                self.umr_graph.triples.append(self.get_number_person('number'))
            # already_added.update({self.ud_node, self.ud_node.parent}) # TODO - FIX

            # attach additional conjuncts, if any
            for num, oc in enumerate((s for s in self.ud_node.siblings if s.deprel == 'conj'), start=3): # and s not in already_added), start=3):
                var_name = next((k for k, v in var_node_mapping.items() if v == oc), None)
                self.umr_graph,triples.append((var_name_conj, f'op{num}', var_name))
                self.umr_graph.triples.append(self.get_number_person(oc, 'number'))  # TODO - FIX
                # already_added.add(oc) # TODO - FIX

            if new_root:
                root_var = var_name_conj

        return root_var

    def copulas(self, copula=True):
        """
        Handle copular constructions by assigning the correct abstract roleset to all configurations.
        If a set of relational terms is provided, it is used here to assign have-rel-role-92.
        """

        replace_arg = None

        if self.ud_node.parent.feats['Case'] in ['Nom', 'Acc'] or (
                self.ud_node.parent.upos in ['NOUN', 'ADJ', 'PROPN', 'PRON'] and not self.ud_node.parent.feats['Case']):

            if self.ud_node.parent.upos == 'ADJ' or (self.ud_node.parent.upos == 'DET' and self.ud_node.parent.feats[
                'PronType'] != 'Prs'):  # TODO: double-check DET (anche ok 'tantus', ma hic sarebbe meglio identity...ma both Dem!!) + remove PRON and do smth with it
                concept = 'have-mod-91'
            elif self.ud_node.parent.upos == 'DET' and self.ud_node.parent.feats['PronType'] == 'Prs':
                concept = 'belong-91'
            elif self.ud_node.parent.upos in ['NOUN', 'PRON']:
                if self.ud_node.parent.upos == 'NOUN' and self.ud_node.parent.lemma in interpersonal:
                    concept = 'have-rel-role-92'
                    replace_arg = 'ARG3'
                else:
                    concept = 'identity-91'
            else:
                concept = 'MISSING'

        elif self.ud_node.parent.feats['NumType'] == 'Card':
            concept = 'have-quant-91'

        elif self.ud_node.parent.feats['Case'] == 'Dat':
            # double dative if ref_dative else dative of possession
            ref_dative = [s for s in self.ud_node.siblings if s.feats['Case'] == 'Dat' and s.deprel == 'obl:arg']
            concept = 'have-purpose-91' if ref_dative else 'belong-91'

        elif self.ud_node.parent.upos == 'VERB' and self.ud_node.parent.feats['VerbForm'] == 'Inf':
            concept = 'have-identity-91'

        else:
            concept = 'MISSING'

        try:
            root_var = self.replace_with_abstract_roleset(concept, replace_arg, overt=copula)
            return root_var

        except (TypeError, AttributeError) as e:
            print(e)
            print(f"Skipping sentence due to missing copular configuration.")

    def relative_clauses(self, rel_pron, role):
        """
        Process relative clauses, by handling:
        1. relative pronoun (rel_pron);
        2. predicate (node);
        3. referent of the whole relative clause (referent).
        """

        referent = None

        if rel_pron == self.ud_node.parent:
            referent = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == rel_pron), None)
            if rel_pron.deprel == 'root':  # can't do anything about root-of, but I can at least save a root
                self.umr_graph.triples.append((None, 'root', referent))
        elif rel_pron.parent == self.ud_node:
            referent = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == self.ud_node.parent), None)
            if rel_pron.udeprel in ['nsubj', 'obj', 'obl']:
                var_pron = next((k for k, v in self.umr_graph.var_node_mapping.items() if v == rel_pron), None)
                self.umr_graph.triples = [tup for tup in self.umr_graph.triples if var_pron not in [tup[0], tup[2]]]  # remove rel_pron

        self.add_node(role, invert=True, def_parent=referent)

        for i, tup in enumerate(self.umr_graph.triples):
            if tup[1] == 'root-of':  # issues with head of relative being the root
                # look for other dependants
                if 'nsubj' in [d.deprel for d in self.ud_node.children]:
                    self.umr_graph.triples[i] = (tup[0], 'actor-of', tup[2])
                elif 'obj' in [d.deprel for d in self.ud_node.children]:
                    self.umr_graph.triples[i] = (tup[0], 'actor-of', tup[2])


    def adverbial_clauses(self):
        """
        Handle adverbial clauses.
        If a dictionary with disambiguated SCONJs is provided, it is used here to assign more fine-grained relations.
        """

        role = self.role

        sconj = next((c for c in self.ud_node.children if c.deprel == 'mark'), None)

        if sconj and sconj.lemma in advcl:
            constraint = advcl.get(sconj.lemma, {}).get('constraint')
            if constraint:
                feat, value = constraint.split('=')
                if sconj.parent.feats[feat] == value:
                    role = advcl.get(sconj.lemma, {}).get('type')

        self.add_node(role)