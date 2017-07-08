from __future__ import division

from bayene.bayesian_network import cussensILPBN
from bayene.utils import cussens_files
from bayene.ilp_model.cussens.solution_controller import convert_to_graph

import matplotlib.pyplot as plt
import networkx as nx

import timeit

with open('test_datasets/parent_3/1000/insurance_1000_1_3.scores', 'r') as test_file:
    test_scores, test_parent_sets = cussens_files.read_cussens_scores(test_file)
    
variablecount = 0

for variable in test_scores:
    variablecount += len(variable.keys())

print('Number of parent variables: ' + str(variablecount))

input("Finished reading the dataset. Press Enter to start the solver.")

classifier_object = cussensILPBN(solver = 'cbc', cycle_finding = True, gomory_cut = True, sink_heuristic = True)

# Record the start time and elapsed time
start_time = timeit.default_timer()

instance, results, progress1, progress2 = classifier_object._fit_scores(test_scores, test_parent_sets)

elapsed = timeit.default_timer() - start_time

print('Time elapsed: ' + str(elapsed))

graph = convert_to_graph(instance.main_model)

# Progress Graph
plt.figure(1)

plt.plot(range(len(progress1)), progress1, 'bs', range(len(progress2)), progress2, 'r--')

# BN
plt.figure(2)

nx.draw_networkx(graph, pos=nx.random_layout(graph))

# Sink Heuristic Performance
sink_performance = []
for i in range(len(progress1)):
    sink_performance.append(((float(progress2[i]) - instance.main_model.objective()) / instance.main_model.objective()))

plt.figure(3)

plt.plot(range(len(sink_performance)), sink_performance, 'g', linewidth=5.0)

plt.show()