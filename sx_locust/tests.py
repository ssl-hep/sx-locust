def locust_task(func):
    """Decorator to mark a function as a ServiceX locust test."""
    func.__is_servicex_locust_test__ = True
    return func

class ServiceXTest:
    @locust_task
    def uproot_raw_query(self):
        from servicex import query, dataset

        spec = {
            "Sample": [
                {
                    "Name": "FuncADL_Uproot_Dict",
                    "Dataset": dataset.FileList(
                        [
                            "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16_13TeV/DAOD_PHYSLITE.37019878._000001.pool.root.1",
                            # noqa: E501
                            "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16_13TeV/DAOD_PHYSLITE.37019878._000002.pool.root.1",
                            # noqa: E501
                            "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16_13TeV/DAOD_PHYSLITE.37019878._000003.pool.root.1",
                            # noqa: E501
                        ]
                    ),
                    "Query": query.FuncADL_Uproot()
                    .FromTree("CollectionTree")
                    .Select(lambda e: {"el_pt": e["AnalysisElectronsAuxDyn.pt"]}),  # type: ignore
                }
            ]
        }

        return spec

    @locust_task
    def func_adl_xaod_simple(self):
        from servicex import query as q, dataset
        query = q.FuncADL_ATLASr22()  # type: ignore
        jets_per_event = query.Select(lambda e: e.Jets("AnalysisJets"))
        jet_info_per_event = jets_per_event.Select(
            lambda jets: {
                "pt": jets.Select(lambda j: j.pt()),
                "eta": jets.Select(lambda j: j.eta()),
            }
        )

        spec = {
            "Sample": [
                {
                    "Name": "func_adl_xAOD_simple",
                    "Dataset": dataset.FileList(
                        [
                            "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/DAOD_PHYSLITE.37622528._000013.pool.root.1",
                            # noqa: E501
                        ]
                    ),
                    "Query": jet_info_per_event,
                }
            ]
        }

        return spec


