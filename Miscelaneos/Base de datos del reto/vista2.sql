use healthData;
CREATE VIEW `ritmo_cardiaco` AS 
SELECT person.username as 'Nombre de Persona', biometrics.heart_rythm as 'Ritmo Cardiaco', state.date as 'Fecha de Medida', state.risk as 'Riesgo de Salud'
FROM healthData.person
JOIN healthData.biometrics
ON person.ID_person = biometrics.ID_person
JOIN healthData.state
ON state.ID_person = biometrics.ID_person
order by state.date ASC;