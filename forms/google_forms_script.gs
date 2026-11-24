/**
 * Crée automatiquement le formulaire Google Forms "Évaluation de l'application web"
 * avec ses 6 sections, ses logiques conditionnelles et une feuille Google Sheets liée
 * qui calcule le "Niveau de satisfaction".
 *
 * Utilisation :
 *   1. Aller sur https://script.google.com  ->  Nouveau projet
 *   2. Effacer le contenu, coller tout ce fichier, enregistrer
 *   3. Choisir la fonction "creerFormulaire" puis cliquer sur "Exécuter" et autoriser l'accès
 *   4. Les liens du formulaire s'affichent dans le "Journal d'exécution"
 */
function creerFormulaire() {
  var ACCORD = ["Tout à fait en désaccord", "En désaccord", "Neutre", "D'accord", "Tout à fait d'accord"];

  var form = FormApp.create("Évaluation de l'application web");
  form.setDescription("Merci de prendre quelques minutes pour évaluer l'application My Data Collection App.");
  form.setProgressBar(true);
  form.setCollectEmail(false);
  form.setConfirmationMessage("Merci pour votre précieux retour ! Vos commentaires nous aideront à améliorer l'application.");

  // ---------------- SECTION 1 : Informations sur l'évaluateur
  form.addSectionHeaderItem().setTitle("SECTION 1 : Informations sur l'évaluateur");
  form.addDateItem().setTitle("Date de l'évaluation").setRequired(true);
  form.addTextItem().setTitle("Votre nom (facultatif)");
  var role = form.addMultipleChoiceItem().setTitle("Votre rôle / profession").setRequired(true);

  // Page affichée seulement si rôle = Autre
  var pageAutre = form.addPageBreakItem().setTitle("Autre profession");
  form.addTextItem().setTitle("Autre profession").setRequired(true);

  var pageUsage = form.addPageBreakItem().setTitle("SECTION 1 (suite) : Utilisation de l'application");
  form.addMultipleChoiceItem().setTitle("Comment avez-vous accédé à l'application ?")
      .setChoiceValues(["Ordinateur", "Tablette", "Smartphone"]).setRequired(true);
  var premiere = form.addMultipleChoiceItem().setTitle("Est-ce votre première utilisation de l'application ?")
      .setRequired(true);

  // Page affichée seulement si première utilisation = Non
  var pageFrequence = form.addPageBreakItem().setTitle("Utilisation antérieure");
  form.addMultipleChoiceItem().setTitle("Combien de fois l'avez-vous utilisée auparavant ?")
      .setChoiceValues(["2 à 3 fois", "4 à 5 fois", "Plus de 5 fois"]);

  // ---------------- SECTION 2 : Première impression et interface
  var pageS2 = form.addPageBreakItem().setTitle("SECTION 2 : Première impression et interface");
  [
    "L'interface est attrayante et bien conçue",
    "L'application est facile à naviguer",
    "Les menus et les boutons sont clairement libellés",
    "L'application se charge rapidement",
    "L'application fonctionne bien sur mon appareil"
  ].forEach(function (q) {
    form.addMultipleChoiceItem().setTitle(q).setChoiceValues(ACCORD).setRequired(true);
  });

  // ---------------- SECTION 3 : Fonctionnalités et performances
  form.addPageBreakItem().setTitle("SECTION 3 : Fonctionnalités et performances");
  form.addCheckboxItem().setTitle("Quelles fonctionnalités avez-vous testées ?")
      .setChoiceValues(["Collecte (scraping) de données", "Téléchargement",
                        "Remplissage du formulaire", "Tableau de bord des données"]).setRequired(true);
  [
    "Les fonctionnalités répondent à mes besoins",
    "Les fonctionnalités sont faciles à utiliser",
    "Les résultats fournis sont précis",
    "L'application m'aide à accomplir mes tâches efficacement",
    "Les instructions et l'aide sont claires et utiles"
  ].forEach(function (q) {
    form.addMultipleChoiceItem().setTitle(q).setChoiceValues(ACCORD).setRequired(true);
  });

  // ---------------- SECTION 4 : Problèmes rencontrés
  form.addPageBreakItem().setTitle("SECTION 4 : Problèmes rencontrés");
  var problemes = form.addMultipleChoiceItem().setTitle("Avez-vous rencontré des problèmes ou des erreurs ?")
      .setRequired(true);

  // Page affichée seulement si problèmes = Oui
  var pageProblemes = form.addPageBreakItem().setTitle("Détail des problèmes");
  form.addCheckboxItem().setTitle("Quel(s) type(s) de problème(s) ?")
      .setChoiceValues(["Erreur de chargement", "Problème d'affichage", "Fonctionnalité non fonctionnelle",
                        "Perte de données", "Performance lente", "Interface confuse", "Autre"]);
  form.addParagraphTextItem().setTitle("Veuillez décrire le(s) problème(s) en détail");

  // ---------------- SECTION 5 : Satisfaction globale
  var pageS5 = form.addPageBreakItem().setTitle("SECTION 5 : Satisfaction globale");
  form.addScaleItem().setTitle("Note globale de l'application").setBounds(0, 10)
      .setLabels("0 - Très mauvais", "10 - Excellent").setRequired(true);
  form.addMultipleChoiceItem().setTitle("Recommanderiez-vous cette application ?")
      .setChoiceValues(["Oui, sans hésiter", "Oui, probablement", "Peut-être", "Probablement pas", "Non"])
      .setRequired(true);
  form.addMultipleChoiceItem().setTitle("Utiliseriez-vous cette application à nouveau ?")
      .setChoiceValues(["Oui, régulièrement", "Oui, occasionnellement", "Peut-être", "Probablement pas", "Non"])
      .setRequired(true);

  // ---------------- SECTION 6 : Suggestions d'amélioration
  form.addPageBreakItem().setTitle("SECTION 6 : Suggestions d'amélioration");
  form.addParagraphTextItem().setTitle("Quels sont les principaux points forts de cette application ?").setRequired(true);
  form.addParagraphTextItem().setTitle("Qu'est-ce qui pourrait être amélioré ?").setRequired(true);
  form.addParagraphTextItem().setTitle("Quelles fonctionnalités manquantes aimeriez-vous voir ajoutées ?");
  form.addParagraphTextItem().setTitle("Commentaires ou suggestions supplémentaires");

  // ---------------- Logiques conditionnelles (aller à la section selon la réponse)
  var roles = ["Étudiant", "Enseignant", "Chercheur", "Analyste de données", "Développeur", "Chef de projet"];
  var choixRoles = roles.map(function (r) { return role.createChoice(r, pageUsage); });
  choixRoles.push(role.createChoice("Autre", pageAutre));
  role.setChoices(choixRoles);

  premiere.setChoices([premiere.createChoice("Oui", pageS2), premiere.createChoice("Non", pageFrequence)]);
  problemes.setChoices([problemes.createChoice("Oui", pageProblemes), problemes.createChoice("Non", pageS5)]);

  // ---------------- Feuille de réponses liée + calcul du niveau de satisfaction
  var ss = SpreadsheetApp.create("Réponses - Évaluation de l'application web");
  ss.setSpreadsheetLocale("en_US"); // garantit que la formule de calcul est comprise
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush();
  try {
    // la feuille des réponses est celle qui est reliée à un formulaire
    var feuille = SpreadsheetApp.openById(ss.getId()).getSheets().filter(function (f) { return f.getFormUrl(); })[0];
    var entetes = feuille.getRange(1, 1, 1, feuille.getLastColumn()).getValues()[0];
    var col = entetes.indexOf("Note globale de l'application") + 1;
    if (col === 0) throw new Error("question 'Note globale' introuvable dans la feuille");
    var lettre = feuille.getRange(1, col).getA1Notation().replace(/\d+/g, "");
    // colonne entière (N:N) : la plage ne se décale pas quand une nouvelle réponse insère une ligne
    var c = lettre + ":" + lettre;
    var derniere = feuille.getLastColumn();
    if (feuille.getMaxColumns() === derniere) feuille.insertColumnAfter(derniere);
    feuille.getRange(1, derniere + 1).setFormula(
      '=ARRAYFORMULA(IF(ROW(' + c + ')=1, "Niveau de satisfaction", IF(' + c + '="", "", ' +
      'IF(' + c + '>=9, "Excellent", IF(' + c + '>=7, "Très bon", ' +
      'IF(' + c + '>=5, "Bon", IF(' + c + '>=3, "Passable", "Médiocre")))))))');
  } catch (e) {
    Logger.log("Colonne de calcul à ajouter à la main (voir GUIDE.md) : " + e);
  }

  try { form.setPublished(true); } catch (e) { Logger.log("Cliquer sur Publier dans le formulaire : " + e); }
  Logger.log("Lien à partager (à mettre dans app.py) : " + form.shortenFormUrl(form.getPublishedUrl()));
  Logger.log("Lien d'édition : " + form.getEditUrl());
  Logger.log("Feuille des réponses : " + ss.getUrl());
}
