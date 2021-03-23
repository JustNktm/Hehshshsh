#!/usr/bin/env python
# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-

#    plotting.py
#
#    Utilities to plot results from PSN analyses.
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



# third-party packages
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
# psntools
from ._util import (
    generate_colorbar,
    generate_heatmap_annotations,
    generate_mask_nancells,
    generate_ticks_positions,
    get_chunk_indexes,
    get_config_plot,
    get_items,
    set_axis)



#--------------------------------- Plot ------------------------------#



def plot_heatmap_nodes(df, \
                       outfile, \
                       configfile, \
                       selected_nodes = None, \
                       nodes_per_page = 20, \
                       psn_labels = None, \
                       node_labels = None):
    """Plot a heatmap with selected nodes on the x-axis and the value
    of a specific metric for different PSNs on the y-axis.

    Parameters
    ----------
    outfile : `str`
        Output PDF file.

    configfile : `str`
        Name of/path to the configuration file to be used for
        plotting.

    selected_nodes : `list`
        Include only these nodes (must be be a list of the nodes'
        string representations).

    nodes_per_page : `int`, default: `20`
        How many nodes to be plotted on each page.

    psn_labels : `list` or `None`, default: `None`
        List of custom labels to be used for the PSNs represented
        in the dataframe. Labels must be passed in the same order
        of the PSNs in the dataframe.

    node_labels : `list` or `None`, default: `None`
        List of custom labels to be used for the nodes represented
        in the dataframe. Labels must be passed in the same order
        of the nodes in the dataframe.

    Returns
    -------
    `None`
    """

    # transpose the dataframe
    df = df.T

    
    #------------------------- Configuration -------------------------#


    # get the plot configuration
    config = get_config_plot(configfile = configfile)
    
    # get the configuration for the output file
    config_out = config["output"]
    
    # get the configurations for the heatmap, the colorbar, the cells
    # with NaN values and the two axes
    config_heat, config_cbar, config_nan, \
    config_xaxis, config_yaxis = \
        get_items(config["plot"]["options"], \
                       ("heatmap", "colorbar", "nancells", \
                        "xaxis", "yaxis"), \
                       {})
    
    # get the configuration for plotting the cells of the heatmap
    # and the annotations
    config_heatmap, config_annot = \
        get_items(config_heat, ("heatmap", "annot"), {})
    
    # get the configuration for the interval to be represented on
    # the colorbar
    config_int = \
        get_items(config_cbar, ("interval",), {})[0]


    #----------------------- Colorbar settings -----------------------#


    # get the colorbar ticks positions
    c_ticks = generate_ticks_positions(values = df.values.flatten(), \
                                       config = config_int).tolist()
            
    # get maximum and minimum value from the interval
    vmin, vmax = c_ticks[0], c_ticks[-1]

    # open the multi-page PDF document
    with PdfPages(outfile) as pdf:

        # if only certain nodes need to be plotted
        if selected_nodes is not None:
            # select only the columns containg such nodes
            df = df[selected_nodes]

        # get the indexes of the chunks of the dataframe containing
        # exactly as many nodes as required by the user (data for
        # each chunk will be plotted on different pages)
        chunk_ixs = get_chunk_indexes(df.T, nodes_per_page)

        # for each chunk
        for start_ix, end_ix in chunk_ixs:


            #-------------------- Data processing --------------------#


            # get a sub-dataframe of the original dataframe
            sub_df = df.iloc[:,start_ix:end_ix]

            # x-axis tick labels will be the column names
            xticklabels = node_labels if node_labels is not None \
                          else sub_df.columns.values.tolist()
            
            # y-axis tick labels will be the row names
            yticklabels = psn_labels if psn_labels is not None \
                          else sub_df.index.values.tolist()
            
            # flatten the array so that we are dealing only with
            # a list of values
            values = sub_df.values.flatten()
            
            # drop NaN values
            yvalues = values[~np.isnan(values)]
            
            # get the cells where the value is NaN (nodes for which
            # the value is not available, i.e. if you PSNs with a
            # different number of nodes)
            nan_cells = np.argwhere(np.isnan(sub_df.values))


            #------------------------- Plot --------------------------#


            # create a new figure
            plt.figure()

            # generate the heatmap annotations
            annots = generate_heatmap_annotations(df = sub_df, \
                                                  config = config_annot)

            # generate the heatmap
            ax = sns.heatmap(sub_df, \
                             cbar = False, \
                             annot = annots[0], \
                             annot_kws = annots[1], \
                             vmin = vmin, \
                             vmax = vmax, \
                             center = (vmax+vmin)/2, \
                             **config_heatmap)

            # add a mask to the NaN cells
            generate_mask_nancells(ax = ax, \
                                   cells = nan_cells, \
                                   config = config_nan)

            # add the colorbar to the heatmap
            generate_colorbar(mappable = ax.get_children()[0], \
                              ticks = c_ticks, \
                              config = config_cbar)

            # set the x-axis
            set_axis(ax = ax, \
                     axis = "x", \
                     ticklabels = xticklabels, \
                     config = config_xaxis)

            # set the y-axis
            set_axis(ax = ax, \
                     axis = "y", \
                     ticks = None, \
                     ticklabels = yticklabels, \
                     config = config_yaxis)
        
            # save the figure to the PDF page
            pdf.savefig(**config_out)
            # clear the figure
            plt.clf()
            # close the current figure window
            plt.close()


def plot_barplot_connected_components(df, \
                                      outfile, \
                                      configfile, \
                                      n_ccs = 5, \
                                      cc_prefix = "CC_", \
                                      psn_labels = None):
    """Plot a barplot with the distribution of nodes in the
    most populated connected components.

    Parameters
    ----------
    df : `pandas.DataFrame`
        Dataframe containing the data.

    outfile : `str`
        Output PDF file.

    configfile : `str`
        Name of/path to the configuration file to be used for
        plotting.

    n_ccs : `int` or `None`, default: `5`
        How many of the most populated connected components
        should be plotted (components will be sorted by size
        starting from the biggest one before plotting).

    cc_prefix : `str`, default: `"CC_"`
        Prefix to add to each connected component's name (if it
        is an empty string, the components' names will be
        integers).

    psn_labels : `list` or `None`, default: `None`
        List of custom labels to be used for the PSNs represented
        in the dataframe. Labels must be passed in the same order
        of the PSNs in the dataframe.

    Returns
    -------
    `None`
    """

    #------------------------- Configuration -------------------------#


    # get the plot configuration
    config = get_config_plot(configfile = configfile)
    
    # get the configuration for the output file
    config_out = config["output"]

    # get the configurations for the barplot and the two axes
    config_bar, config_xaxis, config_yaxis = \
        get_items(config["plot"]["options"], \
                       ("barplot", "xaxis", "yaxis"), \
                       {})

    # get the configuration of the interval represented on the y-axis
    config_int = get_items(config_yaxis, ("interval",), {})[0]


    #------------------------ Data processing ------------------------#


    # get the mean size of the connected components over the PSNs
    mean = df.mean(axis = 0)   
    # get the standard deviation of the size of the connected
    # components over the PSNs 
    std = df.std(axis = 0)


    #---------------------------- Plotting ---------------------------#


    # clear the figure
    plt.clf()
    # close the current figure window
    plt.close()

    # get the y-axis ticks positions
    y_ticks = generate_ticks_positions(values = df.values.flatten(), \
                                       config = config_int).tolist()

    # tick labels of the x-axis will be the PSN labels
    xticklabels = psn_labels if psn_labels is not None else df.columns

    # generate figure and axis
    fig, ax = plt.subplots()

    # generate the barplot
    plt.bar(x = range(len(df.columns)), \
            height = mean, \
            yerr = std, \
            **config_bar)

    # detach a bit the x-axis from the bars.
    # NB: IT NEEDS TO GO BEFORE THE X-AXIS SETTING BECAUSE OTHERWISE
    # THE FONT PROPERTIES OF THE LABELS RESET TO THE DEFAULT
    ax.spines["bottom"].set_position(("outward", 10))

    # set the x-axis
    set_axis(ax = ax, \
             axis = "x", \
             ticks = list(range(len(xticklabels))), \
             ticklabels = xticklabels, \
             config = config_xaxis)

    # set the y-axis
    set_axis(ax = ax, \
             axis = "y", \
             ticks = y_ticks, \
             config = config_yaxis)

    # hide top and right sping
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    # save the plot
    plt.savefig(outfile, **config_out)



