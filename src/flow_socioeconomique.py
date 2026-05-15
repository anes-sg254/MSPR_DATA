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


@flow(name="flow-socioeconomique", task_runner=ConcurrentTaskRunner())
def flow_socioeconomique():
    print("Flow socioéconomique exécuté sur :", socket.gethostname())

    demographie = run_script.submit("etl_demographie.py")
    economie = run_script.submit("etl_economie.py")
    emploi = run_script.submit("etl_emploi.py")
    securite = run_script.submit("etl_securite.py")

    demographie.wait()
    economie.wait()
    emploi.wait()
    securite.wait()


if __name__ == "__main__":
    flow_socioeconomique.serve(
        name="deployment-socioeconomique",
        pause_on_shutdown=False
    )