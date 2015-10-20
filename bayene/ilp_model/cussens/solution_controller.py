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
	
	# Gurobi
	if solver == 'gurobi':
		options["LogFile"] = '' # No log file
		options["Threads"] = 4 # Single thread only for evaluation purposes
		options["MIPFocus"] = 2
		options["ScaleFlag"] = 0
		options["Cuts"] = 0 # Global Cut Off
		if gomory_cut: options["GomoryPasses"] = 20000000 # Turn on Gomory Fractional Cut (Unlimited number)

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
	current_problem = main_model.model_writer(scores_input, parents_input)
	# Generate solver options for the solver selected
	solver_options = generate_solver_options(solver_input, gomory_cut_input)

	# Solution Process Control
	optimal_solution_found = False
	solver_results = None
	best_solution = None

	best_cutoff_value = - sys.maxint
	
	objective_progress = []
	heuristic_progress = []

	while optimal_solution_found == False:
		# Print empty lines between each iteration for better readability
		print ''
		if sink_heuristic:
			print 'Current cutoff value = ' + str(best_cutoff_value)
		
		# Send the current problem to the solver
		solver_results = bayene.ilp_solver.call_solver(current_problem.main_model, solver_options, solver = solver, warmstart = True)
		
		# If the problem is found infeasible, stop the solving process
		if solver_results.solver.termination_condition == TerminationCondition.infeasible:
			optimal_solution_found = True
			continue
		else:
			print 'Current problem solved successfully, Objective Value = ' + str(current_problem.main_model.objective())
				
		# Get all the non-zero variables in the main model		
		current_non_zero_solution = {}
		
		# We need float() and .value because non_zero_value here is a Pyomo object (Don't make a fuss with Pyomo functions)
		for non_zero_key, non_zero_value in current_problem.main_model.chosen_parent_variable.iteritems():
			if float(non_zero_value.value) > 0.0:
				current_non_zero_solution[(non_zero_key[0], non_zero_key[1])] = float(non_zero_value.value)
						
		########################
		#### Cutting Planes ####
		########################
		
		# Cluster (Sub-IP)
		# Generate IP Cluster Cut Finding Model
		print 'Searching for CLUSTER CUTS..'
		cluster_cut_applied = False

		# Generate cluster cut sub-ip problem
		cluster_cuts_sub_ip_problem = cluster_cut_model.model_writer(current_non_zero_solution, len(scores_input), parents_input)
		cluster_cuts_sub_ip_solver_options = {}
		cluster_cuts_sub_ip_solver_options["LogFile"] = ''
		
		# Send the cluster cut IP problem to the solver
		cluster_cuts_sub_ip_solver_results = bayene.ilp_solver.call_solver(cluster_cuts_sub_ip_problem.main_model,
																		   cluster_cuts_sub_ip_solver_options, solver=solver)
		
		# If the problem was properly solved (objective should be strictly larger than -1)
		if cluster_cuts_sub_ip_solver_results.solver.termination_condition == TerminationCondition.optimal \
		and cluster_cuts_sub_ip_problem.main_model.objective() > -1:
		
			# Check if found cluster size > 0
			cluster_members = [node_key for node_key in xrange(len(scores_input))
							   if float(cluster_cuts_sub_ip_problem.main_model.cluster_member_variable[node_key].value) > 0]
			
			if len(cluster_members) > 0:
				print 'Adding CLUSTER cuts to new problem.'
				current_problem.add_cluster_cuts(cluster_members)
				cluster_cut_applied = True
			else:
				print 'NO CLUSTER cuts applicable.'
		else:				
			print 'NO CLUSTER cuts applicable. Cluster Cut Sub-IP could not be solved.'
		
		# Cycle cuts
		cycle_cut_applied = False
		if cycle_finding_input:
			print 'Searching for CYCLE cuts..'
			cycles_found = find_cycles(current_problem.main_model)
			if len(cycles_found) > 0:
				print 'Adding CYCLE cuts to new problem.'
				current_problem.add_cycle_cuts(cycles_found)
				cycle_cut_applied = True
			else:
				print 'NO CYCLE cuts applicable.'
		
		####################
		#### Heuristics ####
		####################
		# Sink-Finding Heuristic
		if sink_heuristic:
			print 'Performing Sink-finding algorithm..'
			heuristic_total_score, heuristic_solutions, sink_heuristic_found = find_sink_heuristic(current_problem)
		
		#####################################
		#### Moving on to Next Iteration ####
		#####################################
		# If either cluster or cycle cut got applied, we should solve the problem again
		if cluster_cut_applied or cycle_cut_applied:
		
			objective_progress.append(current_problem.main_model.objective())
			# If we have a heuristic solution, substitute current_problem with new_problem (which contains a heuristic solution)
			# to allow the solver to make use of the solution.
			if sink_heuristic and sink_heuristic_found:
				print 'Sink heuristic solution score = ' + str(heuristic_total_score)
				
				# Use the total score obtained to be used as cutoff value
				if heuristic_total_score > best_cutoff_value:
					best_cutoff_value = heuristic_total_score

				# solver_options["Cutoff"] = best_cutoff_value
				heuristic_progress.append(best_cutoff_value)
				
				# Clear all the current variable values
				current_problem.main_model.chosen_parent_variable.reset()
				
				# Insert the solutions found from sink-finding for warmstart
				for heuristic_key, heuristic_value in heuristic_solutions.iteritems():
					current_problem.main_model.chosen_parent_variable[(heuristic_key[0], heuristic_key[1])].set_value(heuristic_value)
					
			# Go to the next iteration of this loop
			continue

		# If we don't we need to solve the problem again, the optimal solution is found.
		print 'INTEGER solution found!'
		best_solution = copy.deepcopy(current_problem)
		optimal_solution_found = True
			
	print 'Final Objective Value: ' + str(best_solution.main_model.objective())
	print 'Number of Cluster Cut Iteration: ' + str(best_solution.add_cluster_cuts_count)
	print 'Number of Cycle Cut Iteration: ' + str(best_solution.add_cycle_cuts_count)
	print 'Number of Total Cycle Cuts: ' + str(best_solution.add_cycle_total_count)
	
	return best_solution, solver_results, objective_progress, heuristic_progress

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
		
	for var_key, var_value in instance.chosen_parent_variable.iteritems():
		if float(var_value.value) > 0.99:
			# Check which nodes are in this parent set candidate
			for parent in parents_input[var_key[1]]:
				bn_graph.add_edge(parent, var_key[0])
								
	return bn_graph