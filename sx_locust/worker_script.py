import sys
import json
import traceback
import logging

def main():
    try:
        # Set up logging to stderr to avoid interfering with JSON output on stdout
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )
        logger = logging.getLogger("ServiceXWorker")

        # Read input from command line arguments
        if len(sys.argv) != 2:
            raise ValueError("Expected exactly one argument: JSON spec file path")

        spec_file = sys.argv[1]

        # Read the spec
        with open(spec_file, 'r') as f:
            data = json.load(f)

        spec = data['spec']
        config_data = data.get('config', {})
        ignore_local_cache = data.get('ignore_local_cache', True)
        progress_bar = data.get('progress_bar', 'none')

        logger.info("ServiceX worker script started")
        logger.info(f"Spec: {spec}")

        # Import ServiceX in the clean subprocess
        from servicex import query, dataset, deliver

        # Reconstruct the spec with proper ServiceX objects
        reconstructed_spec = {
            "Sample": []
        }

        for sample in spec["Sample"]:
            # Reconstruct Dataset
            if sample["Dataset"]["type"] == "FileList":
                dataset_obj = dataset.FileList(sample["Dataset"]["files"])
            else:
                raise ValueError(f"Unknown dataset type: {sample['Dataset']['type']}")

            # Reconstruct Query
            if sample["Query"]["type"] == "UprootRaw":
                query_obj = query.UprootRaw(sample["Query"]["data"])
            else:
                raise ValueError(f"Unknown query type: {sample['Query']['type']}")

            # Reconstruct Sample
            reconstructed_sample = {
                "Name": sample["Name"],
                "Dataset": dataset_obj,
                "Query": query_obj,
            }
            reconstructed_spec["Sample"].append(reconstructed_sample)

        # Execute the ServiceX query
        logger.info("Executing ServiceX query...")
        result = deliver(
            reconstructed_spec,
            ignore_local_cache=ignore_local_cache,
            progress_bar=progress_bar
        )

        logger.info("ServiceX query completed successfully")

        # Convert result to serializable format
        serializable_result = {}
        for key, value in result.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # Convert iterables to lists for serialization
                try:
                    serializable_result[key] = list(value)
                except Exception:
                    serializable_result[key] = str(value)
            else:
                serializable_result[key] = value

        # Output result as JSON
        output = {
            'success': True,
            'result': serializable_result,
            'error': None
        }

        # Ensure output goes to stdout and is properly flushed
        print("SERVICEX_RESULT_START", flush=True)
        print(json.dumps(output), flush=True)
        print("SERVICEX_RESULT_END", flush=True)

    except Exception as e:
        # Output error as JSON
        error_output = {
            'success': False,
            'result': None,
            'error': {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
        }

        # Ensure error output also goes to stdout and is properly flushed
        print("SERVICEX_RESULT_START", flush=True)
        print(json.dumps(error_output), flush=True)
        print("SERVICEX_RESULT_END", flush=True)

        sys.exit(1)

if __name__ == "__main__":
    main()