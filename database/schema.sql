CREATE TABLE elections (
    code_commune VARCHAR(255),
    commune VARCHAR(255),
    inscrits INT,
    abstentions INT,
    votants INT,
    blancs INT,
    nuls INT,
    exprimes INT,
    annee INT,
    taux_abstention FLOAT,
    PRIMARY KEY (code_commune, annee)
);
CREATE TABLE economie (
    code_commune VARCHAR(5),
    commune VARCHAR(255),
    creations_total FLOAT,
    creations_industrie FLOAT,
    creations_construction FLOAT,
    creations_commerce_transport FLOAT,
    creations_info_com FLOAT,
    creations_finance FLOAT,
    creations_immo FLOAT,
    creations_services_admin FLOAT,
    creations_adm_sante_social FLOAT,
    creations_autres_services FLOAT,
    annee INT,
    PRIMARY KEY (code_commune, annee)
);

CREATE TABLE securite (
    code_commune VARCHAR(255),
    annee INT,
    indicateur VARCHAR(255),
    nombre FLOAT,
    taux FLOAT,

    PRIMARY KEY (code_commune, annee, indicateur)
);

CREATE TABLE emploi (
    code_commune VARCHAR(255),
    annee INT,
    tranche_age VARCHAR(255),
    demandeurs_emploi INT,

    PRIMARY KEY (code_commune, annee, tranche_age)
);
CREATE TABLE demographie (
    code_commune VARCHAR(255),
    annee INT,
    commune VARCHAR(100),
    population INT,
    part_jeunes FLOAT,
    part_seniors FLOAT,
    indice_jeunesse FLOAT,
    PRIMARY KEY (code_commune, annee)
);

CREATE OR REPLACE VIEW emploi_agrege AS
SELECT
    code_commune,
    annee,
    SUM(CASE WHEN tranche_age = 'Total' THEN demandeurs_emploi ELSE 0 END) AS emploi_total,
    SUM(CASE WHEN tranche_age = 'Moins de 25 ans' THEN demandeurs_emploi ELSE 0 END) AS emploi_moins_25,
    SUM(CASE WHEN tranche_age = 'De 25 à 49 ans' THEN demandeurs_emploi ELSE 0 END) AS emploi_25_49,
    SUM(CASE WHEN tranche_age = '50 ans et plus' THEN demandeurs_emploi ELSE 0 END) AS emploi_50_plus
FROM emploi
GROUP BY code_commune, annee;

CREATE OR REPLACE VIEW securite_agregee AS
SELECT
    code_commune,
    annee,
    SUM(nombre) AS nombre_infractions_total,
    AVG(taux) AS taux_infractions_moyen
FROM securite
GROUP BY code_commune, annee;


CREATE OR REPLACE VIEW dataset_final AS
SELECT
    e.code_commune,
    e.commune,
    e.annee,

    e.inscrits,
    e.abstentions,
    e.votants,
    e.blancs,
    e.nuls,
    e.exprimes,
    e.taux_abstention,

    d.population,
    d.part_jeunes,
    d.part_seniors,
    d.indice_jeunesse,

    emp.emploi_total,
    emp.emploi_moins_25,
    emp.emploi_25_49,
    emp.emploi_50_plus,

    eco.creations_total,
    eco.creations_industrie,
    eco.creations_construction,
    eco.creations_commerce_transport,
    eco.creations_info_com,
    eco.creations_finance,
    eco.creations_immo,
    eco.creations_services_admin,
    eco.creations_adm_sante_social,
    eco.creations_autres_services,

    sec.nombre_infractions_total,
    sec.taux_infractions_moyen

FROM elections e
LEFT JOIN demographie d
    ON e.code_commune = d.code_commune
   AND e.annee = d.annee
LEFT JOIN emploi_agrege emp
    ON e.code_commune = emp.code_commune
   AND e.annee = emp.annee
LEFT JOIN economie eco
    ON e.code_commune = eco.code_commune
   AND e.annee = eco.annee
LEFT JOIN securite_agrege sec
    ON e.code_commune = sec.code_commune
   AND e.annee = sec.annee;