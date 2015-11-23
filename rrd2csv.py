#!/usr/bin/env python
"""Dumps data from all RRAs in a CMDB RRD file to a single CSV.

This script extracts the average and max values for INOCTETS and OUTOCTETS
across all RRAs and combines them into a single CSV file using the highest
resolution available for each time period. If the CSV already exists, only new
data will be appended.

Usage:
    $ python rrd2csv.py <rrd_file> <csv_file>
"""
from __future__ import print_function
from itertools import chain, izip
from math import isnan
from sys import argv, stderr, exit
import lxml.etree
import subprocess
import csv
import os


def comment_content(c):
    """Return the inner content from an XML comment. Strips surrounding
    whitespace."""
    content = str(c)[4:-3]
    return content.strip()


def ts(c):
    """Return the unix and human readable timestamp components of an RRD XML
    date comment."""
    date, tstamp = comment_content(c).split("/")
    return (int(tstamp.strip()), date.strip())


def timestamps(tree, rra_index):
    """Extract timestamps from comments."""
    timestamp_nodes = tree.xpath("//rra[%s]/database/comment()" % rra_index)
    return (ts(c) for c in timestamp_nodes)


def values(tree, rra_index):
    """Extracts INOCTETS and OUTOCTETS from an RRA"""
    row_nodes = tree.xpath("//rra[%s]/database/row" % rra_index)
    for rn in row_nodes:
        yield (float(rn[0].text), float(rn[1].text))


def dump_combined_rra(tree, rra_index, num_rras):
    """Dumps AVERAGE and MAX RRAs that have the same resolution"""
    tstamps = timestamps(tree, rra_index)
    avg_values = values(tree, rra_index)
    max_values = values(tree, rra_index+num_rras)

    # Combine the lists
    for row in izip(tstamps, avg_values, max_values):
        yield chain(row[0], row[1], row[2])


def dump_xml(rrd_file):
    """Parse the XML file and combine the RRAs"""
    tree = lxml.etree.parse(rrd_file)

    num_rras = len(tree.xpath("//rra")) / 2
    rras = []
    for i in reversed(range(1, num_rras+1)):
        rras.append(dump_combined_rra(tree, i, num_rras))

    for i, rra in enumerate(rras):
        if i < num_rras-1:
            next_rra_row = list(next(rras[i+1]))
        else:
            next_rra_row = None

        for row in rra:
            row = list(row)

            # Check if we can switch to the higher resolution RRA
            if next_rra_row is not None and row[0] >= next_rra_row[0]:
                yield next_rra_row
                break

            yield row


def xml_to_csv(rrd_file, out, headers=True, threshold_epoch=None):
    """Dump relevant data from CMDB RRD to a single CSV.

    Args:
        rrd_file (string): Path to XML dump of RRD file
        out (file-like object): Where to write the output
        headers (bool): Whether to include the header row
        threshold_epoch (int): Values from times up to and including this time
            will not be dumped.
    """
    w = csv.writer(out)

    if headers:
        w.writerow(["EPOCH", "DATETIME", "INOCTETS_AVG", "OUTOCTETS_AVG", "INOCTETS_MAX", "OUTOCTETS_MAX"])

    for row in dump_xml(rrd_file):
        # Skip rows from before the threshold epoch
        if threshold_epoch is not None and row[0] <= threshold_epoch:
            continue
        # Skip rows with no data
        if isnan(row[2]) and isnan(row[3]) and isnan(row[4]) and isnan(row[5]):
            continue
        w.writerow(row)


if __name__ == "__main__":
    # Dump the RRD file to XML for parsing
    xml_file = "/tmp/{}.xml".format(argv[1].split('/')[-1])
    subprocess.check_call(["rrdtool", "dump", argv[1], xml_file])

    with open(argv[2], 'a+') as f:
        last_line = None
        headers = True
        threshold_epoch = None

        for line in f:
            last_line = line

        if last_line is not None:
            headers = False
            try:
                threshold_epoch = int(last_line.split(',')[0])
            except ValueError:
                pass

        xml_to_csv(xml_file, f, headers=headers, threshold_epoch=threshold_epoch)

    os.remove(xml_file)
