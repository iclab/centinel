import os
import logging

from centinel.experiment import Experiment
from centinel.primitives import dnslib


class DNSExperiment(Experiment):
    name = "dns_example"

    def __init__(self, input_file):
        self.input_file = input_file
        self.results = []

    def run(self):
        # lookup all the given domains
        domains = []
        for line in self.input_file:
            domains.append(line.strip())
        lookup_results = dnslib.lookup_domains(domains)
        lookup_results['exp-name'] = "lookups"
        self.results.append(lookup_results)
        chaos_results = dnslib.send_chaos_queries()
        chaos_results["exp-name"] = "chaos"
        self.results.append(chaos_results)
