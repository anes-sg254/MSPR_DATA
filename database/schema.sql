CREATE TABLE commune(
   code_commune VARCHAR(5),
   commune VARCHAR(255),
   PRIMARY KEY(code_commune)
);

CREATE TABLE donnees_securite(
   id_securite serial,
   code_commune VARCHAR(5) NOT NULL,
   annee INT NOT NULL,
   vols_avec_armes INT,
   vols_violents_sans_arme INT,
   vols_sans_violence_personnes INT,
   cambriolages_logement INT,
   vols_vehicule INT,
   vols_dans_vehicules INT,
   vols_accessoires_vehicules INT,
   degradations_volontaires INT,
   usage_stupefiants INT,
   violences_intrafamiliales INT,
   violences_hors_famille INT,
   violences_sexuelles INT,
   PRIMARY KEY(id_securite),
   UNIQUE(annee,code_commune),
   FOREIGN KEY(code_commune) REFERENCES commune(code_commune)
);

CREATE TABLE donnees_economie(
   id_economie serial,
   code_commune VARCHAR(5) NOT NULL,
   commune VARCHAR(255),
   annee INT NOT NULL,
   creations_total INT,
   creations_industrie INT,
   creations_construction INT,
   creations_commerce_transport INT,
   creations_info_com INT,
   creations_finance INT,
   creations_immo INT,
   creations_services_admin INT,
   creations_adm_sante_social INT,
   creations_autres_services INT,
   UNIQUE(annee,code_commune),
   PRIMARY KEY(id_economie),
   FOREIGN KEY(code_commune) REFERENCES commune(code_commune)
);

CREATE TABLE donnees_demographie(
   id_demographie serial,
   code_commune VARCHAR(5) NOT NULL,
   commune VARCHAR(255),
   annee INT NOT NULL,
   population INT,
   part_jeunes DECIMAL(15,2),
   part_seniors DECIMAL(15,2),
   indice_jeunesse DECIMAL(15,2), 
   UNIQUE(annee,code_commune),
   PRIMARY KEY(id_demographie),
   FOREIGN KEY(code_commune) REFERENCES commune(code_commune)
);

CREATE TABLE donnees_emploi(
   id_emploi serial,
   code_commune VARCHAR(5) NOT NULL,
   annee INT NOT NULL,
   emploi_total INT,
   emploi_moins_25 INT,
   emploi_25_49 INT,
   emploi_50_plus INT,
   UNIQUE(annee,code_commune),
   PRIMARY KEY(id_emploi),
   FOREIGN KEY(code_commune) REFERENCES commune(code_commune)
);

CREATE TABLE parti(
   id_parti INT,
   nom_parti VARCHAR(255),
   PRIMARY KEY(id_parti)
);

CREATE TABLE election(
   id_election INT,
   annee INT NOT NULL,
   type_election VARCHAR(255),
   unique(annee,type_election),
   PRIMARY KEY(id_election)
);

CREATE TABLE candidat(
   id_candidat INT,
   nom VARCHAR(255),
   prenom VARCHAR(255),
   id_parti INT NOT NULL,
   PRIMARY KEY(id_candidat),
   FOREIGN KEY(id_parti) REFERENCES parti(id_parti)
);

CREATE TABLE participation(
   code_commune VARCHAR(5),
   id_election INT,
   inscrits INT,
   abstentions INT,
   votants INT,
   blancs INT,
   nuls INT,
   exprimes INT,
   taux_abstention DECIMAL(15,2),
   PRIMARY KEY(code_commune, id_election),
   FOREIGN KEY(code_commune) REFERENCES commune(code_commune),
   FOREIGN KEY(id_election) REFERENCES Election(id_election)
);

CREATE TABLE resultat(
   code_commune VARCHAR(5),
   id_candidat INT,
   id_election INT,
   voix INT,
   PRIMARY KEY(code_commune, id_candidat, id_election),
   FOREIGN KEY(code_commune) REFERENCES commune(code_commune),
   FOREIGN KEY(id_candidat) REFERENCES candidat(id_candidat),
   FOREIGN KEY(id_election) REFERENCES Election(id_election)
);

CREATE OR REPLACE VIEW resultat_parti AS
SELECT
    r.code_commune,
    r.id_election,
    e.annee,
    p.id_parti,
    p.nom_parti,
    r.voix
FROM resultat r
JOIN candidat c
    ON r.id_candidat = c.id_candidat
JOIN parti p
    ON c.id_parti = p.id_parti
JOIN election e
    ON r.id_election = e.id_election;



CREATE OR REPLACE VIEW resultat_parti_agrege AS
SELECT
    code_commune,
    annee,
    id_parti,
    nom_parti,
    SUM(voix) AS voix_parti
FROM resultat_parti
GROUP BY code_commune, annee, id_parti, nom_parti;


CREATE OR REPLACE VIEW parti_gagnant AS
SELECT DISTINCT ON (code_commune, annee)
    code_commune,
    annee,
    id_parti,
    nom_parti AS parti_gagnant,
    voix_parti
FROM resultat_parti_agrege
ORDER BY code_commune, annee, voix_parti DESC;

DROP TABLE IF EXISTS dataset_final_2;

CREATE TABLE dataset_final_2 AS
SELECT
    pg.code_commune,
    c.commune,
    pg.annee,
    pg.parti_gagnant,
    pg.voix_parti,

    p.inscrits,
    p.abstentions,
    p.votants,
    p.blancs,
    p.nuls,
    p.exprimes,
    p.taux_abstention,

    d.population,
    d.part_jeunes,
    d.part_seniors,
    d.indice_jeunesse,

    ROUND((emp.emploi_total::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_emploi_total,
    ROUND((emp.emploi_moins_25::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_emploi_moins_25,
    ROUND((emp.emploi_25_49::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_emploi_25_49,
    ROUND((emp.emploi_50_plus::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_emploi_50_plus,

    ROUND((eco.creations_total::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_total,
    ROUND((eco.creations_industrie::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_industrie,
    ROUND((eco.creations_construction::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_construction,
    ROUND((eco.creations_commerce_transport::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_commerce_transport,
    ROUND((eco.creations_info_com::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_info_com,
    ROUND((eco.creations_finance::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_finance,
    ROUND((eco.creations_immo::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_immo,
    ROUND((eco.creations_services_admin::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_services_admin,
    ROUND((eco.creations_adm_sante_social::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_adm_sante_social,
    ROUND((eco.creations_autres_services::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_creations_autres_services,

    ROUND((sec.vols_avec_armes::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_vols_avec_armes,
    ROUND((sec.vols_violents_sans_arme::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_vols_violents_sans_arme,
    ROUND((sec.vols_sans_violence_personnes::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_vols_sans_violence_personnes,
    ROUND((sec.cambriolages_logement::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_cambriolages_logement,
    ROUND((sec.vols_vehicule::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_vols_vehicule,
    ROUND((sec.vols_dans_vehicules::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_vols_dans_vehicules,
    ROUND((sec.vols_accessoires_vehicules::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_vols_accessoires_vehicules,
    ROUND((sec.degradations_volontaires::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_degradations_volontaires,
    ROUND((sec.usage_stupefiants::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_usage_stupefiants,
    ROUND((sec.violences_intrafamiliales::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_violences_intrafamiliales,
    ROUND((sec.violences_hors_famille::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_violences_hors_famille,
    ROUND((sec.violences_sexuelles::numeric * 100 / NULLIF(d.population, 0))::numeric, 2) AS pct_violences_sexuelles

FROM parti_gagnant pg
JOIN commune c
    ON pg.code_commune = c.code_commune
LEFT JOIN participation p
    ON pg.code_commune = p.code_commune
LEFT JOIN election e
    ON p.id_election = e.id_election
   AND pg.annee = e.annee
LEFT JOIN donnees_demographie d
    ON pg.code_commune = d.code_commune
   AND pg.annee = d.annee
LEFT JOIN donnees_emploi emp
    ON pg.code_commune = emp.code_commune
   AND pg.annee = emp.annee
LEFT JOIN donnees_economie eco
    ON pg.code_commune = eco.code_commune
   AND pg.annee = eco.annee
LEFT JOIN donnees_securite sec
    ON pg.code_commune = sec.code_commune
   AND pg.annee = sec.annee;