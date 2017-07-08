"""
bayesian_network.py: This is the main entry point to classifiers in Bayene package,
with class definitions for the variations of Bayesian Network classifiers provided by Bayene.
"""
import os
from pyutilib.services import TempfileManager

from bayene.ilp_model import cussens

class cussensILPBN():

	def __init__(self, score_type='bdeu', n_parents=2, 
	             solver='gurobi',
				 cycle_finding=True, gomory_cut=True, sink_heuristic=True, **kwargs):
		# Get all the temp files to the current working directory
		TempfileManager.tempdir = os.getcwd()
		
		# Record the options to the object
		self.score_type = score_type
		self.n_parents = n_parents
		self.solver = solver
		
		# Cutting Plane-related options
		self.cycle_finding = cycle_finding
		self.gomory_cut = gomory_cut
		
		# Extra optimisation options
		self.sink_heuristic = sink_heuristic
		
		# Process additional user constraints
		if 'extra_constraints' in kwargs:
			self.extra_constraints = kwargs['extra_constraints']
		else:
			self.extra_constraints = None
	
	def fit(self, X):
		# (1) Generate Parent Sets
		_generate_parent_sets()
		
		# (2) Calculate the scores
		# self.scores = scorer.calculate_scores(X, self.parent_candidates, score_type = self.score_type)

		# (3) Insert the scores into the model and solve the model
		self.model_instance, self.result = _fit_scores(self.scores, self.parent_candidates)
		
		return self

	def predict(self, X):
		# (4) Inference - use the graph structure
		pass
	
	def _generate_parent_sets():
		# Do something with self.parent_candidates, along with self.n_parents
		pass

	def _fit_scores(self, scores, parent_candidates):
		if self.extra_constraints:
			return cussens.solve_model(scores, parent_candidates, 
		            self.solver, 
					cycle_finding=self.cycle_finding, gomory_cut=self.gomory_cut, 
					sink_heuristic=self.sink_heuristic, extra_constraints=self.extra_constraints
			)
		else:
			return cussens.solve_model(scores, parent_candidates, 
		            self.solver, cycle_finding=self.cycle_finding, gomory_cut=self.gomory_cut,
					sink_heuristic=self.sink_heuristic
			)