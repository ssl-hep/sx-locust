minikube-mount: minikube mount $LOCAL_DIR:/mnt/sx-locust
helm-install: sleep 5; cd $LOCAL_DIR && helm install -f $VALUES_FILE sx-locust helm/ && tail -f /dev/null
port-forward-locust: sleep 15 && kubectl port-forward svc/sx-locust-scheduler 8089:8089
