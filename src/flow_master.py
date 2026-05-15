from prefect import flow
from prefect.deployments import run_deployment
import socket


@flow(name="flow-master")
def flow_master():
    print("Flow master exécuté sur :", socket.gethostname())

    run_deployment(
        name="flow-referentiels/deployment-referentiels",
        timeout=0
    )

    run_deployment(
        name="flow-socioeconomique/deployment-socioeconomique",
        timeout=0
    )

    run_deployment(
        name="flow-electoral/deployment-electoral",
        timeout=0
    )


if __name__ == "__main__":
    flow_master.serve(
        name="deployment-master",
        pause_on_shutdown=False
    )