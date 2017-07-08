"""
main_model.py: We define the class 'model_writer' for our main ILP model, which essentially is a collection of
the main Pyomo model object and functions to create additional Constraint objects within the main model object
if needed during the solution process.
"""
from pyomo.environ import *

class model_writer():
    
    def __init__(self, scores, parents):
        # Main Model Object
        self.scores = scores
        self.parents = parents
        self.main_model = ConcreteModel()
        
        self.add_cluster_cuts_count = 0
        self.add_cycle_cuts_count = 0
        self.add_cycle_total_count = 0
        self.add_branching_count = 0
    
        # Create range sets representing nodes and parents
        self.main_model.nodes_set = RangeSet(0, len(scores) - 1)
    
        # Only consider candidates that are actually feasible for each nodes (variables)
        def actual_parent_candidate_rule(model):
            return [(node, candidate) for node in model.nodes_set for candidate in self.scores[node].keys()]
    
        self.main_model.candidates_set = Set(initialize = actual_parent_candidate_rule, dimen=2)
    
        # Decision Variable
        self.main_model.chosen_parent_variable = Var(self.main_model.candidates_set, domain = Binary)
    
        # Objective
        def maximise_global_score_rule(model):      
            return sum(self.scores[node][candidate] * model.chosen_parent_variable[node, candidate]
                       for (node, candidate) in model.candidates_set)

        self.main_model.objective = Objective(rule = maximise_global_score_rule, sense = maximize)

        # Constraint
        # Only one parent set should be selected for each nodes
        def only_one_parent_set_rule(model, node):
            return sum(model.chosen_parent_variable[node, candidate]
                       for candidate in [matching[1] for matching in model.candidates_set if matching[0] == node]) == 1
    
        self.main_model.only_one_parent_set_constraint = Constraint(self.main_model.nodes_set, rule = only_one_parent_set_rule)

    def add_cluster_cuts(self, cluster_members):        
        self.add_cluster_cuts_count += 1

        def cluster_constraint_rule(model):
            return sum(model.chosen_parent_variable[candidate]
            for node in cluster_members
            for candidate in model.candidates_set if candidate[0] == node and not set(cluster_members).isdisjoint(self.parents[candidate[1]])
            ) <= len(cluster_members) - 1
        
        # Add the cluster cuts to the main model
        self.main_model.add_component('clusterCons'+str(self.add_cluster_cuts_count)+'_branch_'+str(self.add_branching_count), Constraint(rule = cluster_constraint_rule))
    
    def add_cycle_cuts(self, cycles):
        # Since add_component in Pyomo requires unique names for each constraints, we assign unique serials
        # to each cycle cut add operations
        self.add_cycle_cuts_count += 1
        self.cycles = cycles
        
        self.add_cycle_total_count += len(self.cycles)
        
        # Defined rule for one cycle
        def cycle_cuts_rule(model, cycle_index):
            return sum(model.chosen_parent_variable[candidate]
            for node in self.cycles[cycle_index]
            for candidate in model.candidates_set if candidate[0] == node and not set(self.cycles[cycle_index]).isdisjoint(self.parents[candidate[1]])
            ) <= len(self.cycles[cycle_index]) - 1
    
        # Generate and add constraints for each cycles found
        self.main_model.add_component('cycleCons'+str(self.add_cycle_cuts_count)+'_branch_'+str(self.add_branching_count)+'_'+str(self.add_cycle_total_count),
                                     Constraint(range(len(self.cycles)), rule=cycle_cuts_rule))

    def add_branching(self, variable_to_branch_key, direction):
        self.add_branching_count += 1
        
        if direction == 'leq':
            self.main_model.add_component('branch_'+str(self.add_branching_count)+'_leq'+'_'+str(variable_to_branch_key),
                                          Constraint(expr=self.main_model.chosen_parent_variable[variable_to_branch_key[0], variable_to_branch_key[1]] == 0))
        elif direction == 'geq':
            self.main_model.add_component('branch_'+str(self.add_branching_count)+'_geq'+'_'+str(variable_to_branch_key),
                                          Constraint(expr=self.main_model.chosen_parent_variable[variable_to_branch_key[0], variable_to_branch_key[1]] == 1))