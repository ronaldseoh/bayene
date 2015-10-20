"""
cussens_files.py:

#########################################################
# OR499 Management Science Dissertation, Lent Term 2015 #
# The London School of Economics and Political Science  #
# Candidate Number 64357                                #
#########################################################
"""
import numpy as np
import sys

def read_cussens_data(data_file_object, names = False, arities = True):
	# Cussens 'data' file structure according to the GOBNILP 1.6.1 manual:
	# We ignore all the comment lines that start with '#'.
	# (Among all the non-comment lines) First line is the total number of BN variables.
	# Second line (if exists) records the actual names of the variables to make the final
	# output more intelligible.
	# Third line shows the arities of the variables: they show how many values each variables
	# can take.
	# The rest of the file should be the record of instances, with each column representing one
	# variable.
	# Since the file format itself cannot directly tell us if variables names or arities are
	# available in the file beforehand, user must specify their existence in parameters.
	# Default values are names=False and arities=True.
	
	dataset_data = []
	dataset_names = []
	dataset_arities = []
	
	# Read the very first line of the file and get the total number of attributes
	n_attributes = int(data_file_object.next().rstrip())
	print "Total number of attributes: " + n_attributes
	
	if names == True:
		dataset_names = data_file_object.next().split()
	else:
		dataset_names = range(n_attributes)
	
	if arities == True:
		dataset_arities = [int(i) for i in data_file_object.next().split()]
	
	n_samples = int(data_file_object.next().rstrip())
	
	dataset_data = np.loadtxt(data_file_object, dtype=int)
	
	# If arities are not given, assume that the number of unique elements for each variables
	# are full arities
	if arities == False:
		for column in dataset_data.T:
			dataset_arities.append(len(np.unique(column)))
	
	return dataset_data, dataset_names, dataset_arities

def read_cussens_scores(score_file_object, n_parents):
	# Cussens 'score' file structure according to the GOBNILP 1.6.1 manual:
	# First line is the total number of BN variables.
	# After that, there are groups of lines for each variable of the dataset.
	# The first line have two numbers: the variable number, and the number of candidate parent sets
	# (ex. 0 10 means the variable is 0th variable and have 10 candidate parent sets).
	# The lines after that are calculated scores for each candidate parent set.
	# First token: Score, 2nd: number of parents, the rest: serial number of parent nodes
	
	# Store scores here
	dataset_scores = []
	dataset_all_parents = []
	
	# Read the very first line of the file and get the total number of attributes
	n_attributes = int(score_file_object.next().rstrip())
	print "Total number of attributes: " + str(n_attributes)
	
	# Read exactly the number of attributes specified by n_attributes, no more
	for line in score_file_object:
		
		current_line_tokens = line.split()
		
		if len(current_line_tokens) == 2:
			current_attribute_serial = int(current_line_tokens[0])
			
			# current_line_tokens[1] shows the number of candidates this attribute have
			loop_counter = int(current_line_tokens[1])
			
			while loop_counter > 0:
				candidate_line_tokens = score_file_object.next().split()
				
				# Create a row (one parent candidate) for dataset_all_parents
				# Check if the candidate being examined was previously detected earlier
				current_candidate = [int(i) for i in candidate_line_tokens[2:]]
				if len(current_candidate) < n_parents:
					current_candidate = current_candidate + [sys.maxint] * (n_parents - len(current_candidate))
				
				# TODO: Fix this 'in' statement
				# Check if the array with exactly same numeric values and sequence exists in Python List (dataset_all_parents)
				# Not referring to exact identity
				
				if current_candidate in dataset_all_parents:
					current_candidate_index = dataset_all_parents.index(current_candidate)
				else:
					dataset_all_parents.append(current_candidate)
					# Create new row for this parent candidate in dataset_scores table
					dataset_scores.append([- sys.maxint] * n_attributes)
					current_candidate_index = len(dataset_all_parents) - 1
				
				# Update the row of this candidate on dataset_scores
				dataset_scores[current_candidate_index][current_attribute_serial] = float(candidate_line_tokens[0])
				
				loop_counter -= 1
	
	# Convert the list to csc_matrix or np array
	dataset_scores = np.array(dataset_scores)
	dataset_all_parents = np.array(dataset_all_parents)
			
	return dataset_scores, dataset_all_parents