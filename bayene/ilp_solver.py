"""
ilp_solver.py: This is Bayene's interface to ILP solvers, which in turn based on
Pyomo's solver interfaces. Every code pieces within Bayene that sends
ILP problems to the solver must use this.
"""

from pyomo.environ import *

class InvalidSolverError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def call_solver(model, options, **kwargs):    
    # For ConcreteModel, no need to create a separate instance
    if 'solver' in kwargs:
        # For CPLEX and Gurobi, make use of their Python APIs
        if kwargs['solver'] == 'gurobi':
            opt = SolverFactory(kwargs['solver'], solver_io='python')
        else:
            opt = SolverFactory(kwargs['solver'])

        # Copy from custom solver options dictionary
        opt.options.update(options)

        # Start the solver
        results = opt.solve(model)
        
        return results
    else:
        raise InvalidSolverError('Given solver choice is not supported or invalid.')