#!/usr/bin/env python
# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-

#    PSN.py
#
#    Module where PSN and PSNGroup live.
#
#    Copyright (C) 2020 Valentina Sora 
#                       <sora.valentina1@gmail.com>
#                       Matteo Tiberti 
#                       <matteo.tiberti@gmail.com> 
#                       Elena Papaleo
#                       <elenap@cancer.dk>
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public
#    License along with this program. 
#    If not, see <http://www.gnu.org/licenses/>.



# standard library
import inspect
import itertools
import logging

# third-party packages
import numpy as np
import MDAnalysis as mda
from MDAnalysis.core.groups import Residue
import pandas as pd
import networkx as nx
import networkx.algorithms.centrality as nxcentr



class PSN:

    """Class implementing a Protein Structure Network (PSN).
    """


    ######################## PRIVATE ATTRIBUTES #######################


    # which attributes are by default associated to each node (they are
    # retrieved from the corresponding `MDAnalysis.core.groups.Residue`
    # instances, therefore they MUST be valid `Residue` attributes).
    _NODE_ATTRS = {"segid", "ix", "resnum", "resname"}

    # which methods are allowed to modify the attributes of a PSN
    # instance after instantiation
    _ALLOWED_TO_SET = {"select_edges", "select_nodes"}  
    
    # metrics that have been implemented
    _METRICS = \
        {"node" : \
            {"degree" : \
                {"method" : "get_degree"}, \
             "betweenness_centrality" : \
                {"method" : "get_betweenness_centrality"}, \
             "closeness_centrality" : \
                {"method" : "get_closeness_centrality"}}, \
         "edge" : {}, \
         "graph" : {}, \
         }



    ######################## PUBLIC ATTRIBUTES ########################


    # which format to use when representing nodes
    # as formatted strings
    NODE_STR_FMT = "{segid}-{resnum}{resname}"

    # default segment identifier if no valid segment ID is provided
    # in the topology
    DEFAULT_SEGID = "SYSTEM"

    
    def __init__(self, \
                 matrix, \
                 universe):
        """Initialize a PSN instance.

        Parameters
        ----------
        matrix : `numpy.array` or `str`
            Adjacency matrix representing the PSN or path to
            a file containing the adjacency matrix.

        universe: `MDAnalysis.Universe`
            Universe representing the system the PSN was
            calculated on.

        Attributes
        ----------
        matrix : `numpy.array`
            Adjacency matrix representing the PSN.

        graph : `networkx.Graph`
            Graph representing the PSN.
        """

        self._matrix = self._get_psn_matrix(matrix = matrix)
        self._graph = self._get_psn_graph(universe = universe)



    ########################### PROPERTIES ############################



    # set the matrix attribute as a property
    @property
    def matrix(self):
        return self._matrix
    # define the attibute setter
    @matrix.setter
    def matrix(self, value):
        # who called the setter
        caller = inspect.stack()[1].function
        # raise an error if a method which is not allowed to
        # modify the attribute tries to do so
        if not caller in self._ALLOWED_TO_SET:
            raise AttributeError("'matrix' cannot be changed after " \
                                 "PSN initialization.")
        # set the attribute
        self._matrix = value  


    # set the graph attribute as a property
    @property
    def graph(self):
        return self._graph
    # define the attribute setter
    @graph.setter
    def graph(self, value):
        # who called the setter
        caller = inspect.stack()[1].function
        # raise an error if a method which is not allowed to
        # modify the attribute tries to do so
        if not caller in self._ALLOWED_TO_SET:
            raise AttributeError("'graph' cannot be changed after " \
                                 "PSN initialization.")
        # set the attribute
        self._graph = value 
    


    ######################### PRIVATE METHODS #########################



    def _get_psn_matrix(self, matrix):
        """Load the matrix and ensure that it is is square 
        and symmetric and that it only has two dimensions.
        """
        
        # if matrix is a string, interpret is as a file path
        if isinstance(matrix, str):
            # load the matrix from the file
            matrix = np.loadtxt(matrix)

        # check the number of dimensions
        if not len(matrix.shape) == 2:
            raise ValueError("The PSN matrix must be two-dimensional.")
        # check that both dimensions of the matrix are of the
        # same size
        if not matrix.shape[0] == matrix.shape[1]:
            raise ValueError("The PSN matrix must be square.")
        # check that the matrix is symmetrix
        if not np.array_equal(matrix, matrix.T):
            raise ValueError("The PSN matrix must be symmetric.")
        # return the matrix
        return matrix


    def _get_psn_graph(self, universe):
        """Return the psn with labeled nodes (labels are
        `MDAnalysis.core.groups.Residue` instances).
        """

        # create a graph from the matrix
        graph = nx.from_numpy_matrix(self.matrix)        
        # map the old node labels to the list of Residue instances
        oldlabels2newlabels = dict(zip(graph.nodes, universe.residues))
        # return the PSN graph with relabeled nodes
        return nx.relabel_nodes(\
                G = graph, \
                mapping = oldlabels2newlabels, \
                copy = True)


    def _fmt_dict_of_nodes(self, d, node_fmt):
        """Format the nodes as either `MDAnalysis.core.groups.Residue`
        instances or strings in a dictionary having nodes
        as keys and some property of theirs as values.
        """

        # if nodes should be Residue instances
        if node_fmt == "residues":
            # just return the dictionary
            return d
        
        # if nodes should be strings
        elif node_fmt == "strings":
            # get the mapping between Residue instances and strings
            residues2strings = self.get_nodes_residues2strings()
            # return the dictionary with nodes converted to strings
            return {residues2strings[n] : v for n, v in d.items()}


    def _fmt_dict_of_edges(self, d, node_fmt):
        """Format the nodes forming the edges as either 
        `MDAnalysis.core.groups.Residue` instances os
        strings in a dictionary having nodes as keys
        and some property of theirs as values.
        """

        # if nodes should be Residue instances
        if node_fmt == "residues":
            # just return the dictionary
            return d
        
        # if nodes should be strings
        elif node_fmt == "strings":
            # get the mapping between Residue instances and strings
            residues2strings = self.get_nodes_residues2strings()
            # return the dictionary with nodes converted to strings
            return \
                {(residues2strings[u], residues2strings[v]) : w \
                 for ((u, v), w) in d.items()}



    ########################### PUBLIC API ############################



    def get_nodes_attributes(self):
        """Return `MDAnalysis.core.groups.Residue`
        attributes for each node.

        Parameters
        ----------
        `None`

        Returns
        -------
        attrs : `list`
            List of dictionaries, each dictionary containing the
            attributes of each node.
        """

        # initialize an empty list to store the attributes
        attrs = []
        
        # for each node
        for node in self.graph.nodes:
            # initialize an empty dictionary to store
            # the attributes of this node
            attr_dict = {}
            # for each attribute
            for a in self._NODE_ATTRS:
                # get its value
                value = getattr(node, a)
                # if the attribute is the segment ID
                # and there is no segment ID
                if a == "segid" and value == "":
                    # assign the default segment ID
                    value = self.DEFAULT_SEGID
                # add the attribute to the dictionary
                attr_dict[a] = value
            # add the dictionary of attributes to the list
            attrs.append(attr_dict)

        # return the list of attributes for all nodes
        return attrs


    def get_nodes_residues2strings(self):
        """Return a mapping between `MDAnalysis.core.groups.Residue`
        instances and their string representations.

        Parameters
        ----------
        `None`

        Returns
        -------
        `dict`
            Dictionary mapping `MDAnalysis.core.groups.Residue`
            instances representing nodes to their string
            representation.
        """

        # get the attributes for each node
        attrs = self.get_nodes_attributes()
        # generate the mapping
        return {node: self.NODE_STR_FMT.format(**a) \
                for node, a in zip(self.graph.nodes, attrs)}


    def get_nodes_strings2residues(self):
        """Return a mapping between the string representations
        of nodes and and their corresponding
        `MDAnalysis.core.groups.Residue` instances.

        Parameters
        ----------
        `None`

        Returns
        -------
        `dict`
            Dictionary mapping string representations
            of nodes to their corresponding
            `MDAnalysis.core.groups.Residue` instances.
        """
        
        # get the attributes for each node
        attrs = self.get_nodes_attributes()
        # generate the mapping
        return {self.NODE_STR_FMT.format(**a) : node \
                for node, a in zip(self.graph.nodes, attrs)}


    def get_metric(self, metric, kind, metric_kws):
        """Compute a given metric for the entire graph, each
        node or each edge.

        Parameters
        ----------
        metric : `str`
            Metric to be computed.

        kind : `str`, [`"graph"`, `"edge"`, `"node"`]
            Type of metric.

        metric_kws : `dict`
            Keyword arguments to be passed to the method
            computing the metric.
        """

        # get the method that computes the metric
        method = self._METRICS[kind][metric]["method"]

        # call the method with the provided keyword arguments
        return getattr(self, method)(**metric_kws)


    def get_edges(self, \
                  min_weight = None, \
                  max_weight = None, \
                  mode = "all", \
                  node_fmt = "residues"):
        """Get the edges of the PSN. You can define a minimum and
        maximum weight they must have to be reported and if only
        intrachain/interchain edges are allowed.

        Parameters
        ----------
        min_weight : `int` or `float` or `None`, default: `None`
            Minimum weight an edge must have to be reported.

        max_weight : `int` or `float` or `None`, default: `None`
            Minimum weight an edge must have to be reported.

        mode : `str` [`"all"`, `"intrachain"`, `"interchain"`],
                default: `"all"`
            Which edges should be selected (all, those between chains
            or within a single chain). It works only if nodes are
            represented by `MDAnalysis.core.groups.Residue` instances.

        node_fmt : `str` [`"residues"`, `"strings"`],
              default: `"residues"`
            Whether to represent nodes as 
            `MDAnalysis.core.groups.Residue` instances
            (`"residues"`) or formatted strings (`"strings"`).

        Returns
        -------
        edges : `dict`
            Dictionary mapping each edge to its weight.
        """

        # if no minimum weight was set, set the minimum to minus
        # infinite (no minimum)
        min_weight = float(min_weight) if min_weight else float("-inf")
        # if no maximum weight was set, set the maximum to infinite
        # (no maximum)
        max_weight = float(max_weight) if max_weight else float("inf")

        # initialize the selected edges to all edges
        selected_edges = set(self.graph.edges)

        # if nodes are represented as Residue instances
        if res_instances:
            
            # if all edges should be kept
            if mode == "all":
                # do nothing, all edges are already selected
                pass     
            
            # if only edges between chains should be kept
            elif mode == "interchain":
                # keep edges if segid is different
                selected_edges = \
                    set([(u, v) for (u, v, weight) \
                         in self.graph.edges(data = "weight") \
                         if u.segid != v.segid])           
            
            # if only edges within single chains should be kept
            elif mode == "intrachain":
                # keep edges if segid is the same
                selected_edges = \
                    set([(u, v) for (u, v, weight) \
                         in self.graph.edges(data = "weight") \
                         if u.segid == v.segid])
            
            # if an unrecognized mode was passed
            else:
                # raise an error
                raise ValueError(f"Unrecognized mode '{mode}.'")

        # get the edges
        edges = {(u, v) : w for (u, v, w) \
                 in self.graph.edges(data = "weight") \
                 if (w >= min_weight and w <= max_weight) \
                 and (u, v) in selected_edges}

        # format the edges in the dictionary and return it
        return self._fmt_dict_of_edges(d = edges, node_fmt = node_fmt)



    #-------------------------- Centrality ---------------------------#



    def get_degree(self, \
                   node_fmt = "residues"):
        """Get the degree of all nodes in the PSN.

        Parameters
        ----------
        node_fmt : `str` [`"residues"`, `"strings"`],
              default: `"residues"`
            Whether to represent nodes as 
            `MDAnalysis.core.groups.Residue` instances
            (`"residues"`) or formatted strings (`"strings"`).

        Returns
        -------
        `dict`
            Dictionary mapping each hub to its degree.
        """

        # get the degree of all nodes
        degree = {n : self.graph.degree[n] for n in self.graph.nodes}

        # format the nodes in the dictionary and return it 
        return self._fmt_dict_of_nodes(d = degree, node_fmt = node_fmt)


    def get_hubs(self, \
                 min_degree = 3, \
                 max_degree = None, \
                 node_fmt = "residues"):
        """Get the hubs of the PSN. A hub is defined as a node
        exceeding a certain degree `min_degree`.

        Parameters
        ----------
        min_degree : `int`, default: `3`
            Minimum degree a node must have to be considered a hub.

        max_degree : `int` or `None`, default: `None`
            Maximum degree for a hub to be reported.

        node_fmt : `str` [`"residues"`, `"strings"`],
              default: `"residues"`
            Whether to represent nodes as 
            `MDAnalysis.core.groups.Residue` instances
            (`"residues"`) or formatted strings (`"strings"`).

        Returns
        -------
        `dict`
            Dictionary mapping each hub to its degree.
        """
        
        # if no maximum degree was set, set it to infinite
        max_degree = max_degree if max_degree else float("inf")
        
        # get the hubs
        hubs = {n : v for n, v \
                in self.get_degree(node_fmt = "residues") \
                if (v >= min_degree and v <= max_degree)}
        
        # format the nodes in the dictionary and return it  
        return self._fmt_dict_of_nodes(d = hubs, node_fmt = node_fmt)


    def get_betweenness_centrality(self, \
                                   node_fmt, \
                                   **kwargs):
        """Compute betweenness centrality for each node of the PSN.
        This function is a wrapper, tailored for PSNs, around 
        `networkx.algorithms.centrality.betweennes_centrality`.

        Parameters
        ----------
        node_fmt : `str` [`"residues"`, `"strings"`],
              default: `"residues"`
            Whether to represent nodes as 
            `MDAnalysis.core.groups.Residue` instances
            (`"residues"`) or formatted strings (`"strings"`).

        **kwargs
            Keyword arguments that will be passed to the
            NetworkX function performing the calculation.

        Returns
        -------
        `dict`
            Dictionary mapping each node to its centrality value.
        """

        # get the betweenness centrality
        c = nxcentr.betweenness_centrality(G = self.graph, **kwargs)

        # format the nodes in the dictionary and return it
        return self._fmt_dict_of_nodes(d = c, \
                                       node_fmt = node_fmt)


    def get_closeness_centrality(self, \
                                 node_fmt, \
                                 **kwargs):
        """Compute closeness centrality for each node of the PSN.
        This function is a wrapper, tailored for PSNs, around 
        `networkx.algorithms.centrality.closeness_centrality`.

        Parameters
        ----------

        node_fmt : `str` [`"residues"`, `"strings"`],
              default: `"residues"`
            Whether to represent nodes as 
            `MDAnalysis.core.groups.Residue` instances
            (`"residues"`) or formatted strings (`"strings"`).

        **kwargs
            Keyword arguments that will be passed to the
            NetworkX function performing the calculation.

        Returns
        -------
        `dict`
            Dictionary mapping each node to its centrality value.
        """

        # get the closeness centrality
        c = nxcentr.closeness_centrality(G = self.graph, **kwargs)

        # format the nodes in the dictionary and return it
        return self._fmt_dict_of_nodes(d = c, \
                                       node_fmt = node_fmt)



    #--------------------------- Clustering --------------------------#



    def get_connected_components(self, \
                                 min_size = None, \
                                 max_size = None, \
                                 ascending = False, \
                                 node_fmt = "residues"):
        """Get the connected components in the PSN.

        Parameters
        ----------
        min_size : `int` or `None`, default: `None`
            Minimum size of a connected component
            to be reported.

        max_size : `int` or `None`, default: `None`
            Maximum size of a connected component
            to be reported.

        ascending : `bool`, default: `False`
            Whether the connected components will be 
            reported in ascending order of size 
            (the smallest ones first).

        node_fmt : `str` [`"residues"`, `"strings"`],
              default: `"residues"`
            Whether to represent nodes as 
            `MDAnalysis.core.groups.Residue` instances
            (`"residues"`) or formatted strings (`"strings"`).

        Returns
        -------
        `list`
            List of sets, each set representing a 
            connected component.
        """

        # default minimum size is 1
        min_size = min_size if min_size else 1
        # default maximum size is the number of nodes in the graph
        max_size = max_size if max_size else len(self.graph.nodes)
        
        # get the connected components
        ccs = sorted(nx.connected_components(G = self.graph), \
                     key = len, \
                     reverse = not ascending)
        
        # sets are usable for single connected components
        # because each node is reported once and only once
        ccs = [set(cc) for cc in ccs \
               if (len(cc) >= min_size and len(cc) <= max_size)]
        
        # if nodes should be Residue instances
        if node_fmt == "residues":
            # just return the connected components
            return ccs
        
        # if nodes should be strings
        elif node_fmt == "strings":
            # get the mapping between Residue instances
            # and formatted strings
            residues2strings = self.get_nodes_residues2strings()
            # return the connected components with nodes as strings
            return [set([residues2strings[n] for n in cc]) \
                    for cc in ccs]



    #------------------------------ Paths ----------------------------#



    def get_shortest_paths(self, \
                           pairs, \
                           node_fmt = "residues"):
        """Get all the shortest paths between given pairs of nodes
        
        Parameters
        ----------
        pairs : any iterable
            Iterable of pairs of nodes represented as strings
            (each pair will be internally converted to a tuple
            so be careful if you want the nodes of the pair to
            be in a particular order).

        node_fmt : `str` [`"residues"`, `"strings"`],
              default: `"residues"`
            Whether to represent nodes as 
            `MDAnalysis.core.groups.Residue` instances
            (`"residues"`) or formatted strings (`"strings"`).

        Returns
        -------
        `dict`
            Dictionary mapping a tuple representing each
            pair of nodes to a dictionary mapping each path
            found between the two nodes to its weight
            (sum of the weights of the edges in the path).
        """
        
        # initialize an empty dictionary to store the
        # shortest paths
        all_sps = {}
        
        # get a mapping between string representations
        # of nodes and Residue instances
        residues2strings = self.get_nodes_residues2strings()
        
        # create a copy of the graph with relabeled nodes
        # (Residue instances can raise issues in calculating
        # shortest paths)
        graph = nx.relabel.relabel_nodes(G = self.graph, \
                                         mapping = residues2strings, \
                                         copy = True)
        
        # for each pair of nodes
        for pair in [tuple(pair) for pair in pairs]:

            # split the pair into source and target nodes
            source, target = pair
            
            # check if their is a list one path between the
            # two nodes of the pair
            has_path = nx.has_path(G = graph, \
                                   source = source, \
                                   target = target)
            
            # inform the user that the pair has no paths
            if not has_path:
                logging.info(f"No paths found between " \
                             f"{source} and {target}.")
                # go on to the next pair
                continue

            # get all the shortest paths
            sps = nx.all_shortest_paths(G = graph, \
                                        source = source, \
                                        target = target, \
                                        weight = "weight")

            # if nodes should be represented as Residue instances
            if node_fmt == "residues":
                # get a mapping between Residue instances
                # and string representations
                strings2residues = self.get_nodes_strings2residues()
                # get the Residue instance of the source node
                source = strings2residues[source]
                # get the Residue instance of the target node
                target = strings2residues[target]

            # add an empty dictionary to store the results
            # of the current pair
            all_sps[(source,target)] = {}
            
            # for each shortest path found
            for sp in sps:
                # get the edges forming the shortest path
                path_edges = \
                    [(sp[i], sp[i+1]) for i in range(len(sp)-1)]
                # sum the weight of the edges to get the weight
                # of the path
                path_weight = \
                    np.sum([graph.edges[u,v]["weight"] \
                            for u,v in path_edges])
                # if nodes should be represented as Residue
                # instances
                if node_fmt == "residues":
                    # convert each node of the path
                    sp = [strings2residues[n] for n in sp]
                # add the path and its weight to the dictionary
                # of paths found for the current pair
                all_sps[(source,target)][tuple(sp)] = path_weight

        # return all shortest paths
        return all_sps



    #---------------------------- Sub-PSNs ---------------------------#



    def select_nodes(self, nodes):
        """Select specific nodes in the PSN. The PSN will
        be modified in place.

        Parameters
        ----------
        nodes : any iterable
            Iterable of strings formatted as specified in the
            `NODE_STR_FMT` attribute, each identifying a node
            in the PSN to be kept.

        Returns
        -------
        `None`
        """
        
        # get a mapping of all formatted strings representing
        # nodes to their corresponding Residue instances
        strings2residues = self.get_nodes_strings2residues()
        # select the nodes of interest
        selected_nodes = [strings2residues[n] for n in nodes]
        # it is necessary to create a copy() of the subgraph in order
        # to have a Graph object and not a simple view of the Graph
        self.graph = \
            self.graph.subgraph(nodes = selected_nodes).copy()
        # update the matrix attribute
        self.matrix = \
            nx.convert_matrix.to_numpy_matrix(G = self.graph)


    def select_edges(self, \
                     min_weight = None, \
                     max_weight = None, \
                     mode = "all"):
        """Select edges in the PSN. The PSN will
        be modified in place.

        Parameters
        ----------
        min_weight : see `PSN.get_edges`

        max_weight : see `PSN.get_edges`

        mode : see `PSN.get_edges`

        Returns
        -------
        `None`
        """
        
        # select the edges of interest
        selected_edges = \
            self.get_edges(min_weight = min_weight, \
                           max_weight = max_weight, \
                           mode = mode, \
                           node_fmt = "residues").keys()
        # it is necessary to create a copy() of the subgraph in order
        # to have a Graph object and not a simple view of the Graph
        self.graph = \
            self.graph.edge_subgraph(edges = selected_edges).copy()
        # update the matrix attribute
        self.matrix = \
            nx.convert_matrix.to_numpy_matrix(G = self.graph)



        
class PSNGroup:

    """Class representing a group of PSNs.
    """

    def __init__(self, \
                 psns = None, \
                 matrices = None, \
                 universes = None, \
                 labels = None):
        """Initialize the PSNGroup.

        Parameters
        ----------
        psns : any iterable of `PSN` instances or `None`,
               default: `None`
            Iterable of `PSN` instances.

        matrices : any iterable of `numpy.array` or of `str`
                   or `None`, default: `None`
            Iterable of `numpy.array` or of strings
            representing files where the matrices are stored.

        universes : any iterable of `MDAnalysis.Universe`
                    instances, default: `None`
            Iterable of `MDAnalysis.Universe` instances.

        labels : any iterable of `str` or `None`, 
                 default: `None`
            Labels to be used for each PSN. If `None`,
            0-based indexing will be used.

        Attributes
        ----------
        psns : `dict`
            Dictionary mapping each PSN label to the
            corresponding `PSN` instance.
        """
        
        # if an iterable of PSN objects was passed
        if psns:
            # just convert the iterable to a list
            psns = list(psns)
        
        # if matrices and universes were passed
        else:
            # create a list of PSN objects
            psns = [PSN(matrix = m, universe = u) \
                    for m, u in zip(matrices, universes)]
        
        # if labels were not passed
        if not labels:
            # create a 0-based indexing
            labels = range(len(psns))

        # create a dictionary mapping each label
        # to the corresponding PSN
        self.psns = dict(zip(labels, psns))



    ######################### PRIVATE METHODS #########################



    def _get_common(self, \
                    items_dict):
        """Generic method to get common items (hubs,
        edges, etc.) between different PSNs.
        """
        
        # get all possible combinations of PSNs for which
        # common items need to be retrieved
        combinations = \
            itertools.chain.from_iterable(\
                [itertools.combinations(self.psns.keys(), i) \
                for i in range(2, len(self.psns)+1)])       
        
        # initialize an empty dictionary to store the results
        results = {}
        
        # for each PSN combination
        for combo in combinations:
            
            # create a set from the keys of each entry in the
            # items dictionary (keys are the items of interest,
            # values are associated values) for each PSN
            # in the current combination
            sets = [set(items_dict[i].keys()) for i in combo]
            
            # find the intersection between the items of the
            # PSNs in the current combination
            inters = set.intersection(*sets)
            
            # store the results for the current combination as
            # a dictionary where the names of the PSNs in the
            # combination are associated to the dictionary of
            # items common to all PSNs in the combination, 
            # associated to the values those items have
            # in each PSN of the combination
            results[combo] = \
                {psn_label : \
                    {e : items_dict[psn_label][e] for e in inters} \
                 for psn_label in combo}
        
        # return the results
        return results



    ########################### PUBLIC API ############################



    #------------------------ Get common items -----------------------#



    def get_common_hubs(self, \
                        min_degree = 1, \
                        max_degree = None):
        """Get the common hubs for each possible subset of PSNs
        in the PSNgroup.

        Parameters
        ----------
        min_degree : see `PSN.get_hubs`

        max_degree : see `PSN.get_hubs`

        Returns
        -------
        `dict`
            Dictionary mapping each subset of PSNs to a dictionary
            having as keys the labels of the PSNs in the subset
            and as values a dictionary containing hubs common to
            all PSNs in the subset, associated to the degree they
            have in each PSN of the subset.
        """

        # initialize an empty dictionary to store all
        # hubs found in the PSNs
        hubs_dict = {}
        
        # for each PSN
        for label, psn in self.psns.items():
            # add the hubs in the PSN to the dictionary
            hubs_dict[label] = psn.get_hubs(min_degree = min_degree, \
                                            max_degree = max_degree, \
                                            node_fmt = "strings")
        
        # return the common hubs for each subset of PSNs
        return self._get_common(items_dict = hubs_dict)


    def get_common_edges(self, \
                         min_weight = None, \
                         max_weight = None, \
                         mode = "all"):
        """Get the common edges for each possible subset of PSNs
        in the PSNgroup.

        Parameters
        ----------
        min_weight : see `PSN.get_edges`

        max_weight : see `PSN.get_edges`

        mode : see `PSN.get_edges`

        Returns
        -------
        `dict`
            Dictionary mapping each subset of PSNs to a dictionary
            having as keys the labels of the PSNs in the subset
            and as values a dictionary containing edges common to
            all PSNs in the subset, associated to the weight they
            have in each PSN of the subset.
        """

        # initialize an empty dictionary to store all
        # edges found in the PSNs
        edges_dict = {}
        
        # for each PSN
        for label, psn in self.psns.items():
            # add the edges in the PSN to the dictionary
            edges_dict[label] = \
                psn.get_edges(min_weight = min_weight, \
                              max_weight = max_weight, \
                              mode = mode, \
                              node_fmt = "strings")
        
        return self._get_common(items_dict = edges_dict)     