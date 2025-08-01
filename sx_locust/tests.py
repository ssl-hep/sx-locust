def locust_test(func):
    """Decorator to mark a function as a ServiceX locust test."""
    func.__is_servicex_locust_test__ = True
    return func

class ServiceXTest:
    @locust_test
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

    @locust_test
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


if __name__ == "__main__":
    import argparse
    from servicex import deliver

    parser = argparse.ArgumentParser(description="Run ServiceX queries standalone")
    parser.add_argument("--query", choices=["func_adl_xaod_typed", "uproot_raw_query"],
                        default="func_adl_xaod_typed",
                        help="Query type to run")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout in seconds")

    args = parser.parse_args()

    user = ServiceXTest()
    if args.query == "uproot_raw_query":
        spec = user.uproot_raw_query()
    elif args.query == "func_adl_xaod_typed":
        spec = user.func_adl_xaod_typed()

    print("Query completed successfully!")
    print(f"Result keys: {list(spec.keys()) if spec else 'None'}")

    result = deliver(
        spec,
        ignore_local_cache=True,
        progress_bar='none'
    )