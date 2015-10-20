# bayene
bayene is a Python package for learning Bayesian network structure from a dataset using integer linear programming solver.
This is a partial implementation of Bartlett and Cussens (2015) (http://dx.doi.org/10.1016/j.artint.2015.03.003), with only a subset of various optimisation techniques originally introduced in the paper. However, the codes are completely independent from Dr. Cussens's reference implementation GOBNILP (https://www.cs.york.ac.uk/aig/sw/gobnilp/). 
Due to several suboptimal design decisions I made while writing this project, the performance is currently worse than GOBNILP even for small-sized datasets. Furthermore, bayene currently only accepts pre-complied score files provided by Dr. Cussens (https://www.cs.york.ac.uk/aig/sw/gobnilp/data/).
