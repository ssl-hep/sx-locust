import asyncio
import subprocess
import json
import tempfile
import os
import sys
from pathlib import Path
from locust import User, task, between
import logging

from sx_locust.config import get_config



class ServiceXUser(User):
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = get_config()
        self.servicex_config = self.config.servicex
        self.test_data_config = self.config.test_data
        self._setup_logging()

        # Set path to the worker script
        self.worker_script_path = Path(__file__).parent / "worker_script.py"

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

    def on_start(self):
        """Called when a user starts"""
        self.logger.info("ServiceX user starting (subprocess mode)")
        self.logger.info(f"ServiceX endpoint: {self.servicex_config.endpoint}")
        self.logger.info(f"Worker script path: {self.worker_script_path}")

        # Validate configuration
        try:
            self.config.validate()
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise

    def on_stop(self):
        """Called when a user stops"""
        self.logger.info("ServiceX user stopping")

    def run_servicex_subprocess(self, spec, timeout=300):
        """
        Run ServiceX in a subprocess and return the result.
        """
        try:
            # Create input data
            input_data = {
                'spec': spec,
                'config': {},
                'ignore_local_cache': True,
                'progress_bar': 'none'
            }

            # Write input to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(input_data, f)
                input_file = f.name

            try:
                # Run the subprocess
                self.logger.debug(f"Running subprocess: python {self.worker_script_path} {input_file}")

                result = subprocess.run(
                    [sys.executable, self.worker_script_path, input_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                self.logger.debug(f"Subprocess exit code: {result.returncode}")
                self.logger.debug(f"Subprocess stdout: {result.stdout}")
                self.logger.debug(f"Subprocess stderr: {result.stderr}")

                if result.returncode != 0:
                    raise RuntimeError(
                        f"ServiceX subprocess failed with exit code {result.returncode}\\nStderr: {result.stderr}")

                # Parse the result from stdout
                stdout_lines = result.stdout.strip().split('\\n')

                # Find the result between markers
                start_idx = None
                end_idx = None

                for i, line in enumerate(stdout_lines):
                    if line.strip() == "SERVICEX_RESULT_START":
                        start_idx = i + 1
                    elif line.strip() == "SERVICEX_RESULT_END":
                        end_idx = i
                        break

                if start_idx is None or end_idx is None:
                    self.logger.error(f"Failed to find result markers. Stdout: {result.stdout}")
                    self.logger.error(f"Stderr: {result.stderr}")
                    raise RuntimeError("Could not find result markers in subprocess output")

                # Get the JSON result
                result_json = '\\n'.join(stdout_lines[start_idx:end_idx])
                try:
                    worker_result = json.loads(result_json)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON result: {e}")
                    self.logger.error(f"Raw JSON string: {result_json}")
                    self.logger.error(f"Full stdout: {result.stdout}")
                    raise RuntimeError(f"Failed to parse JSON result: {e}")

                return worker_result

            finally:
                # Clean up input file
                if os.path.exists(input_file):
                    os.unlink(input_file)

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ServiceX subprocess timed out after {timeout} seconds")
        except Exception as e:
            self.logger.error(f"Subprocess execution failed: {e}")
            raise

    @task
    def uproot_raw_query(self):
        """Execute a ServiceX query using UprootRaw in a subprocess"""

        self.logger.info("Starting uproot_raw_query task")

        # Create spec with raw data
        file_list = [
            "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16_13TeV/DAOD_PHYSLITE.37019878._000001.pool.root.1",
            "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16_13TeV/DAOD_PHYSLITE.37019878._000002.pool.root.1",
            "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16_13TeV/DAOD_PHYSLITE.37019878._000003.pool.root.1",
        ]

        spec = {
            "Sample": [
                {
                    "Name": "UprootRaw_Dict",
                    "Dataset": {
                        "type": "FileList",
                        "files": file_list
                    },
                    "Query": {
                        "type": "UprootRaw",
                        "data": [
                            {
                                "treename": "CollectionTree",
                                "filter_name": "AnalysisElectronsAuxDyn.pt",
                            }
                        ]
                    },
                }
            ]
        }

        try:
            self.logger.debug("Running ServiceX in subprocess...")

            worker_result = self.run_servicex_subprocess(spec, timeout=300)

            if worker_result['success']:
                self.logger.info("ServiceX query completed successfully")
                self.logger.debug(
                    f"Result keys: {list(worker_result['result'].keys()) if worker_result['result'] else 'None'}")
            else:
                error_info = worker_result['error']
                self.logger.error(f"ServiceX worker failed: {error_info['type']}: {error_info['message']}")
                self.logger.debug(f"Worker traceback: {error_info['traceback']}")
                raise RuntimeError(f"ServiceX worker failed: {error_info['message']}")

        except Exception as e:
            self.logger.error(f"ServiceX query failed: {str(e)}")
            raise
