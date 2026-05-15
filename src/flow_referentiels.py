from prefect import flow, task
import subprocess
import socket


@task(name="Lancer un script ETL")
def run_script(script_name: str):
    print("Conteneur courant :", socket.gethostname())
    print(f"--- Lancement de {script_name} ---")

    result = subprocess.run(
        ["python", script_name],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.stderr:
        print(f"Erreur dans {script_name} :")
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"Le script {script_name} a échoué.")


@flow(name="flow-referentiels")
def flow_referentiels():
    print("Flow référentiels exécuté sur :", socket.gethostname())

    run_script("etl_commune.py")
    run_script("etl_parti_candidat_election.py")


if __name__ == "__main__":
    flow_referentiels.serve(
        name="deployment-referentiels",
        pause_on_shutdown=False
    )