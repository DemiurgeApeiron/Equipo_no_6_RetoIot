use healthData;
CREATE VIEW `o2` AS 
SELECT person.username as 'Nombre de Persona', biometrics.oxigen_level as 'Nivel de Oxigeno', state.date as 'Fecha de Medida'
FROM healthData.person
JOIN healthData.biometrics
ON person.ID_person = biometrics.ID_person
JOIN healthData.state
ON state.ID_person = biometrics.ID_person
order by state.date ASC