import gzip
from elderberry import ReturnParser
from graphio import NodeSet, RelationshipSet

TAXID_SPECIFIC_GENEINFO = {
    '9606': 'Homo_sapiens.gene_info.gz',
    '10090': 'Mus_musculus.gene_info.gz'
}


class NcbiGeneParser(ReturnParser):

    def __init__(self, root_dir):

        super(NcbiGeneParser, self).__init__(root_dir)

        # arguments
        self.arguments = ['taxid']

        # output data
        self.genes = NodeSet(['Gene'], merge_keys=['sid'])

        self.genesymbols = NodeSet(['GeneSymbol'], merge_keys=['sid', 'taxid'])
        self.genesymbol_synonym_genesymbol = RelationshipSet('SYNONYM', ['GeneSymbol'], ['GeneSymbol'],
                                                             ['sid', 'taxid'], ['sid', 'taxid'])
        self.gene_maps_genesymbol = RelationshipSet('MAPS', ['Gene'], ['GeneSymbol'], ['sid'], ['sid', 'taxid'])

    def run_with_mounted_arguments(self):
        self.run(self.taxid)

    def run(self, taxid):
        ncbigene_instance = self.get_instance_by_name('NcbiGene')

        # get org specific gene_info file if available
        if taxid in TAXID_SPECIFIC_GENEINFO:
            gene_info_file = ncbigene_instance.get_file(TAXID_SPECIFIC_GENEINFO[taxid])
        else:
            gene_info_file = ncbigene_instance.get_file('gene_info.gz')

        self.parse_gene_info(gene_info_file, taxid)

    def parse_gene_info(self, gene_info_file, taxid):
        # check sets
        check_ids = set()
        check_ids_symbols = set()

        with gzip.open(gene_info_file, 'rt') as f:

            header = next(f)

            # account for different formatting of header line (leading "#Format: " or not)
            if header.startswith('#Format:'):
                header_fields = tuple(header.split(':')[1].split('(')[0].rstrip().lstrip().split())
            elif header.startswith('#tax'):
                header_fields = tuple(
                    header[1:].strip().split('\t')
                )
            else:
                raise AttributeError("File header was reformatted: {0}".format(header))

            for l in f:

                flds = l.rstrip().split('\t')

                this_taxid = flds[0]
                if this_taxid == taxid:

                    # (Gene)
                    entrez_gene_id = flds[1]
                    if entrez_gene_id not in check_ids:
                        props = {'sid': entrez_gene_id, 'source': 'ncbigene'}
                        # update with all fields
                        props.update(
                            zip(header_fields, flds)
                        )

                        check_ids.add(entrez_gene_id)
                        self.genes.add_node(props)

                    # (GeneSymbol) and (GeneSymbol)-[SYNONYM]-(GeneSymbol)
                    primary_symbol = flds[2]
                    synonym_symbols = flds[4].split('|')

                    # add primary symbol node
                    if primary_symbol not in check_ids_symbols and primary_symbol != '-':
                        check_ids_symbols.add(primary_symbol)
                        self.genesymbols.add_node({'sid': primary_symbol,
                                                   'taxid': taxid})

                    for synonym in synonym_symbols:
                        # GeneSymbol-[SYNONYM]-GeneSymbol
                        self.genesymbol_synonym_genesymbol.add_relationship({'sid': synonym, 'taxid': taxid},
                                                                            {'sid': primary_symbol,
                                                                             'taxid': taxid},
                                                                            {'source': 'ncbigene'})

                        if synonym not in check_ids_symbols and synonym != '-':
                            check_ids_symbols.add(synonym)
                            self.genesymbols.add_node({'sid': synonym,
                                                       'status': 'synonym',
                                                       'taxid': taxid})

                    # (Gene)-[MAPS]-(GeneSymbol)
                    # primary
                    self.gene_maps_genesymbol.add_relationship({'sid': entrez_gene_id},
                                                               {'sid': primary_symbol, 'taxid': taxid},
                                                               {'source': 'ncbigene', 'status': 'primary'})
                    # synonym
                    for symbol in synonym_symbols:
                        self.gene_maps_genesymbol.add_relationship({'sid': entrez_gene_id},
                                                                   {'sid': symbol, 'taxid': taxid},
                                                                   {'source': 'ncbigene', 'status': 'synonym'})


class NcbiGeneOrthologParser(ReturnParser):

    def __init__(self, root_dir):
        """

        :param ncbigene_instance: NcbiGene Instance
        :type ncbigene_instance: DataSourceInstance
        :param taxid:
        """
        super(NcbiGeneOrthologParser, self).__init__(root_dir)

        self.gene_ortholog_gene = RelationshipSet('ORTHOLOG', ['Gene'], ['Gene'], ['sid'], ['sid'])

        self.object_sets = [self.gene_ortholog_gene]
        self.container.add_all(self.object_sets)

    def run_with_mounted_arguments(self):
        self.run()

    def run(self):
        """
        Get the Gene-ORTHOLOG-Gene relationships. This is currently not filteres for taxid.
        """
        ncbigene_instance = self.get_instance_by_name('NcbiGene')
        ortholog_file = ncbigene_instance.get_file('gene_orthologs.gz')

        with gzip.open(ortholog_file, 'rt') as f:
            # skip first line
            next(f)

            for l in f:
                flds = l.strip().split()
                g1 = flds[1]
                g2 = flds[4]

                self.gene_ortholog_gene.add_relationship(
                    {'sid': g1}, {'sid': g2}, {}
                )
