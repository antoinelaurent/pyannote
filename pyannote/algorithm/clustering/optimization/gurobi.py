#!/usr/bin/env python
# encoding: utf-8

import os
import socket
os.putenv('GRB_LICENSE_FILE', 
          "%s/licenses/%s.lic" % (os.getenv('GUROBI_HOME'),
                                  socket.gethostname()))
import gurobipy as grb

import sys
import numpy as np
import networkx as nx
from graph import LabelNode, IdentityNode
from pyannote.base.annotation import Unknown

optimization_status = {
    grb.GRB.LOADED: 'Model is loaded, but no solution information is '
                    'available.',
    grb.GRB.OPTIMAL: 'Model was solved to optimality (subject to tolerances), '
                     'and an optimal solution is available.',
    grb.GRB.INFEASIBLE: 'Model was proven to be infeasible.',
    grb.GRB.INF_OR_UNBD: 'Model was proven to be either infeasible or '
                         'unbounded.',
    grb.GRB.UNBOUNDED: 'Model was proven to be unbounded.',
    grb.GRB.CUTOFF: 'Optimal objective for model was proven to be worse than '
                    'the value specified in the Cutoff parameter. No solution '
                    'information is available.',
    grb.GRB.ITERATION_LIMIT: 'Optimization terminated because the total number '
                             'of simplex iterations performed exceeded the '
                             'value specified in the IterationLimit parameter, '
                             'or because the total number of barrier '
                             'iterations exceeded the value specified in the '
                             'BarIterLimit parameter.',
    grb.GRB.NODE_LIMIT: 'Optimization terminated because the total number of '
                        'branch-and-cut nodes explored exceeded the value '
                        'specified in the NodeLimit parameter.',
    grb.GRB.TIME_LIMIT: 'Optimization terminated because the time expended '
                        'exceeded the value specified in the TimeLimit '
                        'parameter.',
    grb.GRB.SOLUTION_LIMIT: 'Optimization terminated because the number of '
                            'solutions found reached the value specified in '
                            'the SolutionLimit parameter.',
    grb.GRB.INTERRUPTED: 'Optimization was terminated by the user.',
    grb.GRB.NUMERIC: 'Optimization was terminated due to unrecoverable '
                     'numerical difficulties.',
    grb.GRB.SUBOPTIMAL: 'Unable to satisfy optimality tolerances; '
                        'a sub-optimal solution is available.'
}


# from progressbar import ProgressBar, Percentage, Bar, ETA

def _n01(g, n1, n2):
    if g.has_edge(n1, n2):
        p = g[n1][n2]['probability']
        if p in [0,1]:
            return int(p)
    return None

def _ij2nn(ij, i2n):
    return i2n[ij[0]], i2n[ij[1]]

class GurobiModel(object):
    """
    
    """
    def __init__(self, G, timeLimit=None, threads=None, quiet=True):
        super(GurobiModel, self).__init__()
        self.graph = G
        self.timeLimit = timeLimit
        self.threads = threads
        self.quiet = quiet
        
        self.model, self.x = self.__model(G)
        
    def __model(self, G):
        """
        Create Gurobi clustering model from graph
    
        Parameters
        ----------
        g : nx.Graph
            One node per track. Edge attribute 'probability' between nodes.
        
        Returns
        -------
        model : gurobipy.grb.Model
            Gurobi clustering model
        x : dict
            Dictionary of gurobi.grb.Var
            x[node, other_node] is a boolean variable indicating whether
            node and other_node are in the same cluster
    
        """
        
        # make sure graph only contains LabelNode(s) and IdentityNode(s)
        bad_nodes = [node for node in G.nodes_iter() 
                          if not isinstance(node, (LabelNode, IdentityNode))]
        if len(bad_nodes) > 0:
            raise ValueError('Graph contains nodes other than'
                             'LabelNode or IdentityNode.')
    
        # pb = ProgressBar(widgets=[None, ' ', Percentage(), ' ', Bar(),' ', ETA()], 
        #                  term_width=80, poll=1, 
        #                  left_justify=True, fd=sys.stderr)
    
        # create empty model & dictionary to store its variables
        model = grb.Model('My model')
        model.setParam('OutputFlag', False)
        
        x = {}
    
        nodes = G.nodes()
        N = len(nodes)
        
        # one variable per node pair
        for i1 in range(N):
            n1 = nodes[i1]
            for i2 in range(i1+1, N):
                n2 = nodes[i2]
                x[n1, n2] = model.addVar(vtype=grb.GRB.BINARY)
        
        model.update()
        
        # transitivity constraints
        # pb.widgets[0] = 'Constraints'
    
        # Σi|1..N ( Σj|i+1..N ( Σk|j+1..N 1 ) ) 
        # pb.maxval = int(N**3/6. - N**2/2. + N/3.)
        # pb.start()
    
        p = {}
        i2n = {}
        for i1 in range(N):
        
            # Σi|1..i1 ( Σj|i+1..N ( Σk|j+1..N 1 ) ) 
            # n = int(N**2*i1/2.- N*i1/2.-N*(i1**2/2.+i1/2.)+i1**3/6.+i1**2/2.+i1/3.)
            # pb.update(n)
        
            n1 = nodes[i1]
            i2n[1] = n1
        
            for i2 in range(i1+1, N):
            
                n2 = nodes[i2]
                i2n[2] = n2
            
                # probability n1 <--> n2
                p[1,2] = _n01(G, n1, n2)
            
                if p[1,2] in [0, 1]:
                    model.addConstr(x[n1, n2] == p[1,2])
            
                for i3 in range(i2+1, N):
                
                    n3 = nodes[i3]
                    i2n[3] = n3
                
                    # probability n1 <--> n3
                    p[1,3] = _n01(G, n1, n3)
                
                    # probability n2 <--> n3
                    p[2,3] = _n01(G, n2, n3)
                
                    # set of values taken by the 3 edges
                    # {0}, {1}, {None}, {0, 1}, {0, None}, {1, None} or {0, 1, None}
                    values_set = set(p.values())
                
                    if not (values_set - set([0, 1])):
                        # there are only 0s and 1s
                        # those constraints will be taken care of by the outer loop
                        continue
                
                    # {0: number of 0s, 1: number of 1s, None: number of Nones}
                    value2count = {v: p.values().count(v) for v in [0, 1, None]}
                    value2list = {v: [ij for ij in p if p[ij] == v] 
                                  for v in [0, 1, None]}
                
                    # 0/1 values
                    values_set = values_set - set([None])
                    num_values = len(values_set)
                
                    # there is only one None
                    if value2count[None] == 1:
                    
                        ij_none = value2list[None][0]
                        ninj_none = _ij2nn(ij_none, i2n)
                        if num_values == 1:
                            # there are one None and two 0s (or two 1s)
                            # set the one None to 0 (or to 1)
                            model.addConstr(x[ninj_none] == values_set.pop())
                        else:
                            # there are one None, one 0 and one 1
                            # set the one None to 0
                            model.addConstr(x[ninj_none] == 0)
                
                    # there are two Nones
                    elif value2count[None] == 2:
                    
                        ij = value2list[None][0]
                        ninj = _ij2nn(ij, i2n)
                        jk = value2list[None][1]
                        njnk = _ij2nn(jk, i2n)
                    
                        if value2count[1] == 1:
                            # there are two Nones and one 1
                            # set the two Nones equal to each other
                            model.addConstr(x[ninj] == x[njnk])
                        else:
                            # there two Nones and one 0
                            # set the two Nones different from each other
                            model.addConstr(x[ninj] + x[njnk] <= 1)
                
                    else:
                        model.addConstr(x[n2, n3] + x[n1, n3] - x[n1, n2] <= 1)
                        model.addConstr(x[n1, n2] + x[n1, n3] - x[n2, n3] <= 1)
                        model.addConstr(x[n1, n2] + x[n2, n3] - x[n1, n3] <= 1)
                
    
        # pb.finish()
    
        if self.timeLimit is not None:
            model.setParam(grb.GRB.Param.TimeLimit, self.timeLimit)
        if self.threads is not None:
            model.setParam(grb.GRB.Param.Threads, self.threads)
        model.setParam(grb.GRB.Param.MIPFocus, 1)
        # model.setParam(grb.GRB.Param.MIPGap, 1e-2)
        
        model.setParam('OutputFlag', not self.quiet)
        
        # return the model & its variables
        return model, x
    
    def setObjective(self, alpha=0.5):
        """
        Set following objective:
        Maximize ∑ α.xij.pij + (1-α).(1-xij).(1-pij)
                j>i
    
        Parameters
        ----------
        alpha : float, optional
            Value of α in above formula
        """
        
        nodes = self.graph.nodes()
        N = len(nodes)
        
        P = np.array(nx.to_numpy_matrix(self.graph, nodelist=nodes,
                                        weight='probability'))
        # normalization coefficient so that objective function
        # ranges between 0 and 1000
        k = 1000. / np.sum([1. for n, node in enumerate(nodes)
                               for m, other_node in enumerate(nodes)
                               if m > n and P[n,m] > 0])
        
        # objective function
        objective = k * grb.quicksum([alpha * P[n,m]*self.x[node,other_node] +
                            (1-alpha)*(1-P[n,m])*(1-self.x[node,other_node]) 
                                      for n, node in enumerate(nodes) 
                                      for m, other_node in enumerate(nodes)
                                      if m > n and P[n,m] > 0])
        
        self.model.setObjective(objective, grb.GRB.MAXIMIZE)
        self.model.setParam(grb.GRB.Param.Method, 2)
    
    def optimize(self):
        self.model.optimize()
    
    def get_status(self):
        status = self.model.getAttr(grb.GRB.Attr.Status)
        return status, optimization_status[status]
    
    def reconstruct(self, annotation):
        """
        Generate new annotation from optimized Gurobi model
        
        Parameters
        ----------
        annotation : Annotation
            Original annotation
    
        Returns
        -------
        new_annotation : dictionary of Annotation
    
        """
        
        g = nx.Graph()
        for (n1, n2), var in self.x.iteritems():
            g.add_node(n1)
            g.add_node(n2)
            if var.x == 1.:
                g.add_edge(n1, n2)
        
        uri = annotation.video
        modality = annotation.modality
        
        translation = {}
        for cc in nx.connected_components(g):
        
            labelNodes = [node for node in cc 
                               if isinstance(node, LabelNode) 
                              and node.uri == uri 
                              and node.modality == modality]
            
            identityNodes = [node for node in cc 
                                  if isinstance(node, IdentityNode)]
            
            if len(identityNodes) > 1:
                raise ValueError('Looks like there are more than one identity '
                                 'in this cluster: %s' % [node.identifier 
                                                    for node in identityNodes])
            elif len(identityNodes) == 1:
                identifier = identityNodes[0].identifier
            else:
                identifier = Unknown()
            
            for node in labelNodes:
                translation[node.label] = identifier
        
        return (annotation % translation).smooth()
        