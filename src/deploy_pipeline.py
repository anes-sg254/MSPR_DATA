from orchestrateur_prefect import pipeline_etl

if __name__ == "__main__":
    pipeline_etl.serve(
        name="deployment-pipeline-mspr",
        pause_on_shutdown=False
    )