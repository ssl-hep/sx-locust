from locust import User, task, between

import logging

from sx_locust.config import get_config
import asyncio

from servicex import query, dataset, deliver


class ServiceXUser(User):
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = get_config()
        self.servicex_config = self.config.servicex
        self.test_data_config = self.config.test_data
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

    def on_start(self):
        """Called when a user starts"""
        self.logger.info("ServiceX user starting")
        self.logger.info(f"ServiceX endpoint: {self.servicex_config.endpoint}")

        # Validate configuration
        try:
            self.config.validate()
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise

    @task
    def uproot_raw_query(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        spec = {
            "Sample": [
                {
                    "Name": "UprootRaw_Dict",
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
                    "Query": query.UprootRaw(
                        [
                            {
                                "treename": "CollectionTree",
                                "filter_name": "AnalysisElectronsAuxDyn.pt",
                            }
                        ]
                    ),
                }
            ]
        }

        print(f"Files: {deliver(spec, ignore_local_cache=True)}")