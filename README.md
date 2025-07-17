# sx-locust
This is a WIP repo for building a ServiceX load testing suite with Locust (https://locust.io/).

# servicex.yaml
Right now this project requires you to mount your local directory with `helm` in order to access your `servicex.yaml` file. The `Procfile` will set this (see instructions below).

You can run `sx-locust` from the same or different cluster that ServiceX is running on. If you are running both on the same cluster (for example, locally with minikube), make sure to use the cluster's internal addresses.
```yaml
# servicex.yaml
api_endpoints:
  - endpoint: http://servicex-servicex-app:8000
    name: servicex-local
    type: uproot

cache_path: /tmp/
shortened_downloaded_filename: true
```

# Values file
See `local-values.sample.yaml` for a basic example on how to modify `sx-locust`'s configuration via a local values file. If you are running `sx-locust` on the same local cluster as `servicex`, you can use the sample file directly.  

# Running with Overmind
Use Overmind to run the `Procfile`. See the example command below, where LOCAL_DIR is the location of your `sx-locust` checkout, and VALUES_FILE is the name of your local values file.

```bash
cd /Users/mattshirley/work/sx-locust && LOCAL_DIR=${pwd} VALUES_FILE=local-values.yaml overmind start
```

This will install the helm chart and open a port forward on 8089. You can then access the Locust web UI at http://localhost:8089. Don't set the number of users greater than the number of workers. If running on the same cluster as `servicex`, set the hots value to http://servicex-servicex-app:8000. Otherwise, use the public url you use to access ServiceX.