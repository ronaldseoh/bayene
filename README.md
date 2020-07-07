# bayene

`bayene` is a Python package for learning Bayesian network structure from a dataset using integer linear programming solver.
This is a partial implementation of [Bartlett and Cussens (2015)](https://link.iamblogger.net/erm2t), with only a subset of various optimisation techniques originally introduced in the paper. However, the codes are completely independent from Dr. Cussens's reference implementation [GOBNILP](https://link.iamblogger.net/j1nqo). 
Due to several suboptimal design decisions I made while writing this project, the performance is currently worse than GOBNILP even for small-sized datasets. Furthermore, bayene currently only accepts pre-complied [score files provided by Dr. Cussens](https://link.iamblogger.net/xroew).

# Report

Read my master's dissertation "Solving Bayesian Network Structure Learning Problem with Integer Linear Programming" from [arXiv](https://link.iamblogger.net/bn-structure-ilp).

# License

`bayene` is licensed under BSD-new license. Please check `LICENSE`.
