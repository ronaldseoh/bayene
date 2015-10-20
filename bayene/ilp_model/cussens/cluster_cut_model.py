"""
cluster_cut_model.py: 
"""
from pyomo.environ import *

class model_writer():
    def __init__(self, current_non_zero_solution, n_variables, parents):
        
        # Main Model Object
        self.main_model = ConcreteModel()
        
        # Non-zero variables I(W->v) in the main problem constitutes a set
        self.main_model.parent_set_variable = Var(current_non_zero_solution.keys(), domain = Binary)
        
        # Among all the variable nodes, we choose the ones to be included in the cluster
        self.main_model.cluster_member_variable = Var(xrange(n_variables), domain = Binary)
        
        # -|C| + sum[x(W->v) * J(W->v)] > -1 ==> sum[x(W->v) * J(W->v)] -|C| > -1
        def cluster_cut_objective_rule(model):
            return sum(current_non_zero_solution[key] * model.parent_set_variable[key] for key in current_non_zero_solution.keys()) - sum(model.cluster_member_variable[node] for node in xrange(n_variables))
        
        self.main_model.objective = Objective(rule = cluster_cut_objective_rule, sense = maximize)
    
        def cluster_child_always_selected_rule(model, key0, key1):
            return model.parent_set_variable[(key0, key1)] == model.cluster_member_variable[key0]
        
        self.main_model.cluster_child_always_selected = Constraint(current_non_zero_solution.keys(), rule = cluster_child_always_selected_rule)
        
        def cluster_parent_at_least_one_rule(model, key0, key1):
            return model.parent_set_variable[(key0, key1)] <= sum(model.cluster_member_variable[parent] for parent in parents[key1])
        
        self.main_model.cluster_parent_at_least_one = Constraint(current_non_zero_solution.keys(), rule = cluster_parent_at_least_one_rule)
        
        self.main_model.cluster_size_at_least_two = Constraint(expr = summation(self.main_model.cluster_member_variable) >= 2)
        
        def objective_bigger_than_minus_one_rule(model):
            return sum(current_non_zero_solution[key] * model.parent_set_variable[key] for key in current_non_zero_solution.keys()) - sum(model.cluster_member_variable[node] for node in xrange(n_variables)) >= -1
        
        self.main_model.objective_bigger_than_minus_one = Constraint(rule = objective_bigger_than_minus_one_rule)