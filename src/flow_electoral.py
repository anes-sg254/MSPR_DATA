from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
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


@flow(name="flow-electoral", task_runner=ConcurrentTaskRunner())
def flow_electoral():
    print("Flow électoral exécuté sur :", socket.gethostname())

    participation = run_script.submit("etl_participation.py")
    resultat = run_script.submit("etl_resultat.py")

    participation.wait()
    resultat.wait()


if __name__ == "__main__":
    flow_electoral.serve(
        name="deployment-electoral",
        pause_on_shutdown=False
    )