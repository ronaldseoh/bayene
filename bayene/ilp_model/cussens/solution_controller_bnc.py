"""
solution_controller.py: 

#########################################################
# OR499 Management Science Dissertation, Lent Term 2015 #
# The London School of Economics and Political Science  #
# Candidate Number 64357                                #
#########################################################
"""
import sys
import copy
import operator
import networkx as nx
from pyomo.opt import TerminationCondition
import bayene.ilp_solver
import main_model
import cluster_cut_model

def generate_solver_options(solver, gomory_cut):
	options = {}
	
	# Configure the options available for each solver
	# For all solvers, turn on Gomory cuts if possible
	if solver == 'gurobi':
		options["Threads"] = 4 # Single thread only for evaluation purposes
		options["LogFile"] = '' # No log file
		options["LazyConstraints"] = 1
		options["Presolve"] = 1
		
	return options

def solve_model(scores, parents, solver, cycle_finding, gomory_cut, sink_heuristic, **kwargs):
	
	# Variables to be globally used throughout ilp_model.cussens module
	# Not using class here because we want everything to be accessed as cussens.<name>
	global scores_input, parents_input, solver_input, cycle_finding_input, gomory_cut_input
	
	scores_input = scores
	parents_input = parents
	solver_input = solver
	cycle_finding_input = cycle_finding
	gomory_cut_input = gomory_cut
	
	# Generate initial problem
	initial_problem = main_model.model_writer(scores_input, parents_input)
	# Generate solver options for the solver selected
	solver_options = generate_solver_options(solver_input, gomory_cut_input)

	# Branch-and-Cut
	optimal_solution_found = False
	solver_results = None
	problem_list = []
	objective_upper_bound = float(- sys.maxint) # Arbitrarily small negative number (maximum supported by the system)
	best_solution = None
	best_solution_solver_results = None
	
	# Add the initial formulation to problem_list
	problem_list.append(initial_problem)
	
	global current_problem
	
	if sink_heuristic:
		best_cutoff_value = - sys.maxint

	while len(problem_list) > 0:
		print ''
		print 'Current best solution = ' + str(objective_upper_bound)
		if sink_heuristic:
			print 'Current cutoff value = ' + str(best_cutoff_value)
		print 'Current number of problems in the list: ' + str(len(problem_list))
		
		# Pop out the first problem on problem_list
		current_problem = problem_list.pop(0)
		
		solver_results = bayene.ilp_solver.call_solver(current_problem.main_model, solver_options, solver = solver, warmstart = True)
		
		# If the problem is found infeasible, stop the solving process and go back to the beginning of the loop
		if solver_results.solver.termination_condition == TerminationCondition.infeasible:
			continue
		else:
			print 'Current problem solved successfully, Objective Value = ' + str(current_problem.main_model.objective())
			
		# New Problem to be added to take all the cuts and heuristics results
		new_problem = copy.deepcopy(current_problem)
				
		########################
		#### Cutting Planes ####
		########################
		
		# Cluster (Sub-IP)
		new_problem_cluster_cut_applied = False
		print('Searching for CLUSTER CUTS..')
		
		# Get all the non-zero variables in the main model
		# Also at the same time, check the solutions to find a non-integer variable.
		
		current_non_zero_solution = {}
		
		for key, value in current_problem.main_model.chosen_parent_variable.iteritems():
			if float(value.value) > 0:
				current_non_zero_solution[key] = float(value.value)
				
		cluster_cuts_sub_ip_problem = cluster_cut_model.model_writer(current_non_zero_solution, len(scores_input), parents_input)
		cluster_cuts_sub_ip_solver_options = {}
		cluster_cuts_sub_ip_solver_options["LogFile"] = ''
		
		# Send the cluster cut IP problem to the solver
		cluster_cuts_sub_ip_solver_results = bayene.ilp_solver.call_solver(cluster_cuts_sub_ip_problem.main_model,
																		   cluster_cuts_sub_ip_solver_options, solver=solver)
		
		if cluster_cuts_sub_ip_solver_results.solver.termination_condition == TerminationCondition.optimal and cluster_cuts_sub_ip_problem.main_model.objective() > -1:
		
			# Check if found cluster size > 0
			cluster_members = [cluster_node for cluster_node in range(len(scores_input)) if cluster_cuts_sub_ip_problem.main_model.cluster_member_variable[cluster_node].value > 0]
			
			if len(cluster_members) > 0:
				print('Adding CLUSTER cuts to new problem.')
				new_problem.add_cluster_cuts(cluster_members)
				new_problem_cluster_cut_applied = True
			else:
				print('NO CLUSTER cuts applicable.')
		else:				
			print('NO CLUSTER cuts applicable. Cluster Cut Sub-IP could not be solved.')
		
		# Cycle cuts
		new_problem_cycle_cut_applied = False
		if cycle_finding_input:
			print('Searching for CYCLE cuts..')
			cycles_found = find_cycles(current_problem.main_model)
			if len(cycles_found) > 0:
				print('Adding CYCLE cuts to new problem.')
				new_problem.add_cycle_cuts(cycles_found)
				new_problem_cycle_cut_applied = True
			else:
				print('NO CYCLE cuts applicable.')
		
		####################
		#### Heuristics ####
		####################
		# Sink-Finding Heuristic
		if sink_heuristic:
			heuristic_total_score, heuristic_solutions, sink_heuristic_found = find_sink_heuristic(current_problem)
		
		if new_problem_cluster_cut_applied or new_problem_cycle_cut_applied:
			if sink_heuristic and sink_heuristic_found:
				print 'Sink heuristic solution score = ' + str(heuristic_total_score)
				
				# Use the total score obtained to be used as cutoff value
				if heuristic_total_score > best_cutoff_value:
					best_cutoff_value = heuristic_total_score
				solver_options["Cutoff"] = best_cutoff_value
				
				# Clear all the current variable values
				new_problem.main_model.chosen_parent_variable.reset()
				
				# Insert the solutions found from sink-finding for warmstart
				for heuristic_key, heuristic_value in heuristic_solutions.iteritems():
					new_problem.main_model.chosen_parent_variable[(heuristic_key[0], heuristic_key[1])].set_value(heuristic_value)	
				
			problem_list.append(new_problem)
			continue
				
		# If current_problem's objective value is lower than objective_upper_bound, move on to the next problem	
		if float(current_problem.main_model.objective()) <= objective_upper_bound:
			print('Objective value is LOWER than or EQUAL to the incumbent.')
			continue
		
		all_solutions_integer = True
		
		variable_to_branch_key = -1
		non_integer_closeness_to_one = sys.maxint
		for parent_key, parent_value in current_problem.main_model.chosen_parent_variable.iteritems():
			if parent_value.value > 0:
				if parent_value.value < 1:
					all_solutions_integer = False
					# Smaller the closer
					if (1.0 - float(parent_value.value)) < non_integer_closeness_to_one:
						variable_to_branch_key = copy.deepcopy(parent_key)
						non_integer_closeness_to_one = 1.0 - float(parent_value.value)

		if all_solutions_integer == True:
			print('INTEGER solution found!')
			objective_upper_bound = float(current_problem.main_model.objective())
			best_solution = copy.deepcopy(current_problem)
			best_solution_solver_results = solver_results
		else:
			# Get the variable to branch on: choose the one that has the closest value to 1
			print 'Branching on ' + str(variable_to_branch_key) + ', ' + str(current_problem.main_model.chosen_parent_variable[variable_to_branch_key].value)
			
			print('BRANCHING..')
			new_problem_branch_1 = copy.deepcopy(current_problem)
			new_problem_branch_2 = copy.deepcopy(current_problem)
			
			# One problem with less than or equal to floor(non-integer)
			new_problem_branch_1.add_branching(variable_to_branch_key, 'leq')
			new_problem_branch_2.add_branching(variable_to_branch_key, 'geq')
			
			problem_list.append(new_problem_branch_1)
			problem_list.append(new_problem_branch_2)
			
	print 'Final Objective Value: ' + str(best_solution.main_model.objective())
	
	return best_solution, best_solution_solver_results

# Make use of not yet optimal solution generated by the solver to find a feasible solution.
def find_sink_heuristic(current_problem):
	
	heuristic_total_score = float(0)
	heuristic_solutions = {}
	variables_to_decide = range(len(scores_input))

	# For each nodes, check the current answers and pick the variable(s) with the answer closest to 1,
	# and choose the one with the highest coefficient (local scores). If that one is ruled out
	# by earlier iteration, choose the next highest scoring one.
	# Just in case all the variables for the node are ruled out before completion,
	# we are unable to a heuristic solution and declare sink_heuristic_applied = False.
	sink_heuristic_found = False
			
	while not sink_heuristic_found:
				
		best_scores_each_node_index = {}
				
		for search_node in variables_to_decide:
			this_node_scores = sorted(scores_input[search_node].items(), key=operator.itemgetter(1), reverse = True)
					
			best_parent_for_this_node = -1
			best_parent_for_this_node_score = float(-1)
			for search_node_parent, search_node_parent_score in this_node_scores:
				if not heuristic_solutions.has_key((search_node, search_node_parent)):
					best_parent_for_this_node = search_node_parent
					best_parent_for_this_node_score = search_node_parent_score
					break
		
			best_scores_each_node_index[search_node] = best_parent_for_this_node
					
		# Among the best parents available selected for nodes, choose the one that has the closest value to 1
		# in current solution.
		node_closest = -1
		node_closest_parent = -1
		current_best_distance = sys.maxint
			
		for best_scores_node, best_scores_parent in best_scores_each_node_index.iteritems():
			distance_to_one = 1.0 - float(current_problem.main_model.chosen_parent_variable[(best_scores_node, best_scores_parent)].value)
			if distance_to_one < current_best_distance:
				node_closest = best_scores_node
				node_closest_parent = best_scores_parent
				current_best_distance = distance_to_one

		# We choose the highest scoring parent candidate (unless already ruled out) as this node will be the sink
		heuristic_solutions[node_closest, node_closest_parent] = 1
				
		# Rule out all the parent candidates that has this node as member
		for other_node in xrange(len(scores_input)):
			for other_node_parent in scores_input[other_node].keys():
				if node_closest in parents_input[other_node_parent]:
					heuristic_solutions[(other_node, other_node_parent)] = 0
				
		# Rule out other candidates for this node
		for this_node_other_parent in scores_input[node_closest].keys():
			if this_node_other_parent <> node_closest_parent:
				heuristic_solutions[node_closest, this_node_other_parent] = 0
				
		variables_to_decide.remove(node_closest)
				
		heuristic_total_score += scores_input[node_closest][node_closest_parent]
				
		if len(variables_to_decide) == 0:
			sink_heuristic_found = True
				
	return heuristic_total_score, heuristic_solutions, sink_heuristic_found

# Use NetworkX Cycle Finding method to find elementary cycles
def find_cycles(instance):
		
	bn_graph = convert_to_graph(instance)
	
	cycles_found = list(nx.simple_cycles(bn_graph))

	return cycles_found

# Convert the solutions returned by solver into NetworkX DiGraph format
def convert_to_graph(instance):
		
	bn_graph = nx.DiGraph()
		
	for key, value in instance.chosen_parent_variable.iteritems():
		if float(value.value) > 0.99:
			# Check which nodes are in this parent set candidate
			for parent in parents_input[key[1]]:
				bn_graph.add_edge(parent, key[0])
								
	return bn_graph