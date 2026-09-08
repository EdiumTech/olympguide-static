//
//  BenefitViewController.swift
//  olympguide
//
//  Created by Tom Tim on 26.02.2025.
//

import UIKit

final class BenefitViewController: UIViewController {
    struct Program {
        let code: String
        let name: String
        let university: String
    }
    
    struct Olympiad {
        let name: String
        let level: Int
        let profile: String
    }
    
    struct Benefit {
        let minClass: Int?
        let minDiplomaLevel: Int?
        let isBVI: Bool
        
        let confirmationSubjects: [BenefitModel.ConfirmationSubject]?
        let fullScoreSubjects: [String]?
        var admissionRule: AdmissionRule? = nil
        var sourceRelation: String? = nil
    }
    
    var program: Program?
    var olympiad: Olympiad?
    var benefit: Benefit?
    
    let informationStackView: UIStackView = UIStackView()
    
    init(
        with viewModel: OlympiadWithBenefitViewModel
    ) {
        self.olympiad = Olympiad(
            name: viewModel.olympiadName,
            level: viewModel.olympiadLevel,
            profile: viewModel.olympiadProfile
        )
        
        self.benefit = Benefit(
            minClass: viewModel.minClass,
            minDiplomaLevel: viewModel.minDiplomaLevel,
            isBVI: viewModel.isBVI,
            confirmationSubjects: viewModel.confirmationSubjects,
            fullScoreSubjects: viewModel.fullScoreSubjects,
            admissionRule: viewModel.admissionRule,
            sourceRelation: viewModel.sourceRelation
        )
        
        super.init(nibName: nil, bundle: nil)
    }

    init(
        with viewModel: ProgramWithBenefitsViewModel, index: Int
    ) {
        self.program = Program(
            code: viewModel.program.field,
            name: viewModel.program.programName,
            university: viewModel.program.university
        )
        let benefitInformation = viewModel.benefitInformation[index]
        self.benefit = Benefit(
            minClass: benefitInformation.minClass,
            minDiplomaLevel: benefitInformation.minDiplomaLevel,
            isBVI: benefitInformation.isBVI,
            confirmationSubjects: benefitInformation.confirmationSubjects,
            fullScoreSubjects: benefitInformation.fullScoreSubjects,
            admissionRule: benefitInformation.admissionRule,
            sourceRelation: benefitInformation.sourceRelation
        )
        super.init(nibName: nil, bundle: nil)
    }
    
    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        modalPresentationStyle = .pageSheet
        if let sheet = sheetPresentationController {
            sheet.detents = [.medium(), .large()]
            sheet.selectedDetentIdentifier = .medium
        }
        
        configureUI()
    }
    
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        let height = informationStackView.frame.height + 20 * 2
        let weight = view.frame.width - 10
        
        self.preferredContentSize = CGSize(width: weight, height: height)
    }
    
    private func configureUI() {
        view.backgroundColor = .white
        
        configureInformatonStack()
        configureOlympiadTitleLabel()
        configureProgramNameLabel()
        configureOlympiadNameLabel()
        configureOlympiadInformation()
        configureBenefitInformationStack()
        configurationConfirmationSubjects()
        configureSourceConditions()
    }
    
    private func configureInformatonStack() {
        let scrollView = UIScrollView()
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        informationStackView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(scrollView)
        scrollView.addSubview(informationStackView)
        informationStackView.axis = .vertical
        informationStackView.spacing = 17
        informationStackView.alignment = .fill
        NSLayoutConstraint.activate([
            scrollView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            scrollView.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            scrollView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            scrollView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            informationStackView.topAnchor.constraint(equalTo: scrollView.contentLayoutGuide.topAnchor, constant: 20),
            informationStackView.bottomAnchor.constraint(equalTo: scrollView.contentLayoutGuide.bottomAnchor, constant: -20),
            informationStackView.leadingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.leadingAnchor, constant: 20),
            informationStackView.trailingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.trailingAnchor, constant: -20),
            informationStackView.widthAnchor.constraint(equalTo: scrollView.frameLayoutGuide.widthAnchor, constant: -40)
        ])
    }

    private func configureSourceConditions() {
        guard let rule = benefit?.admissionRule else { return }
        let text = UILabel()
        text.numberOfLines = 0
        text.font = .preferredFont(forTextStyle: .body)
        let relation = benefit?.sourceRelation == "school_conditions"
            ? "Условия физтех-школы. Применимость к конкурсной группе определяется текстом правила."
            : "Условия применяются совместно; учитывайте область действия и исключения."
        text.text = "Приём \(rule.admissionYear)\n\n\(relation)\n\n\(rule.details)"
        informationStackView.addArrangedSubview(text)
        let source = UIButton(type: .system)
        source.setTitle("Открыть официальный источник", for: .normal)
        source.addTarget(self, action: #selector(openOfficialSource), for: .touchUpInside)
        informationStackView.addArrangedSubview(source)
    }

    @objc private func openOfficialSource() {
        guard let rule = benefit?.admissionRule,
              var components = URLComponents(string: rule.sourceURL),
              components.scheme == "https" else { return }
        if let page = rule.location?["page"] { components.fragment = "page=\(page)" }
        guard let url = components.url else { return }
        UIApplication.shared.open(url)
    }

    private func configureOlympiadTitleLabel() {
        let olympiadTitleLabel: UILabel = UILabel()
        olympiadTitleLabel.font = FontManager.shared.font(for: .tableTitle)
        olympiadTitleLabel.textColor = .black
        olympiadTitleLabel.text = "Льгота"
        olympiadTitleLabel.textAlignment = .center
        
        informationStackView.addArrangedSubview(olympiadTitleLabel)
        
        olympiadTitleLabel.pinCenterX(to: informationStackView.centerXAnchor)
    }
    
    private func configureProgramNameLabel() {
        guard let program = self.program else { return }
        let nameLabel: UILabel = UILabel()
        nameLabel.font = FontManager.shared.font(for: .commonInformation)
        nameLabel.numberOfLines = 0
        nameLabel.lineBreakMode = .byWordWrapping
        
        nameLabel.text = program.name
        
        informationStackView.addArrangedSubview(nameLabel)
    }
    
    private func configureOlympiadNameLabel() {
        guard let olympiad = self.olympiad else { return }
        let nameLabel: UILabel = UILabel()
        nameLabel.font = FontManager.shared.font(for: .commonInformation)
        nameLabel.numberOfLines = 0
        nameLabel.lineBreakMode = .byWordWrapping
        
        nameLabel.text = olympiad.name
        
        informationStackView.addArrangedSubview(nameLabel)
    }
    
    private func configureOlympiadInformation() {
        let olympiadInformationStack = UIStackView()
        
        olympiadInformationStack.axis = .vertical
        olympiadInformationStack.spacing = 7
        olympiadInformationStack.distribution = .fill
        olympiadInformationStack.alignment = .leading
        
        configureCodeLabel(olympiadInformationStack)
        configureUniversityLabel(olympiadInformationStack)
        configureLevelLabel(olympiadInformationStack)
        configureProfileLabel(olympiadInformationStack)
        configureClassLebel(olympiadInformationStack)
        configureMinDiplomaLabel(olympiadInformationStack)
        
        informationStackView.addArrangedSubview(olympiadInformationStack)
    }
    
    private func configureCodeLabel(_ stack: UIStackView) {
        guard let program = self.program else { return }
        let codeLabel: UILabel = UILabel()
        codeLabel.font = FontManager.shared.font(for: .additionalInformation)
        codeLabel.textColor = UIColor(hex: "#787878")
        codeLabel.text = "Код направления: \(program.code)"
        
        stack.addArrangedSubview(codeLabel)
    }
    
    private func configureUniversityLabel(_ stack: UIStackView) {
        guard let program = self.program else { return }
        let universitLabel: UILabel = UILabel()
        universitLabel.font = FontManager.shared.font(for: .additionalInformation)
        universitLabel.textColor = UIColor(hex: "#787878")
        universitLabel.text = "Вуз: \(program.university)"
        
        stack.addArrangedSubview(universitLabel)
    }
    
    private func configureLevelLabel(_ stack: UIStackView) {
        guard let olympiad = self.olympiad, olympiad.level > 0 else { return }

        let levelLabel: UILabel = UILabel()
        levelLabel.font = FontManager.shared.font(for: .additionalInformation)
        levelLabel.textColor = UIColor(hex: "#787878")
        levelLabel.text = "Уровень: \(String(repeating: "I", count: olympiad.level))"
        
        stack.addArrangedSubview(levelLabel)
    }
    
    private func configureProfileLabel(_ stack: UIStackView) {
        guard let olympiad = self.olympiad else { return }
        let profileLabel: UILabel = UILabel()
        profileLabel.font = FontManager.shared.font(for: .additionalInformation)
        profileLabel.textColor = UIColor(hex: "#787878")
        profileLabel.numberOfLines = 0
        profileLabel.lineBreakMode = .byWordWrapping
        profileLabel.text = "Профиль: \(olympiad.profile)"
        
        stack.addArrangedSubview(profileLabel)
    }
    
    private func configureClassLebel(_ stack: UIStackView) {
        guard let benefit = self.benefit, let grade = benefit.minClass else { return }
        let classLabel: UILabel = UILabel()
        classLabel.font = FontManager.shared.font(for: .additionalInformation)
        classLabel.textColor = UIColor(hex: "#787878")
        classLabel.text = "Класс: \(grade)"
        
        stack.addArrangedSubview(classLabel)
    }
    
    private func configureMinDiplomaLabel(_ stack: UIStackView) {
        guard let benefit = self.benefit, benefit.minDiplomaLevel != nil else { return }
        let minDiplomaLabel = UILabel()
        minDiplomaLabel.font = FontManager.shared.font(for: .additionalInformation)
        minDiplomaLabel.textColor = UIColor(hex: "#787878")
        let minDiplomaLevelText = benefit.minDiplomaLevel == 1 ? "победитель" : "призёр"
        
        minDiplomaLabel.text = "Диплом: \(minDiplomaLevelText)"
        stack.addArrangedSubview(minDiplomaLabel)
    }
    
    private func configureBenefitInformationStack() {
        guard let benefit = self.benefit else { return }
        let benefitInformationStack = UIStackView()
        
        benefitInformationStack.axis = .vertical
        benefitInformationStack.spacing = 7
        benefitInformationStack.distribution = .fill
        benefitInformationStack.alignment = .leading
        
        benefitInformationStack.addArrangedSubview(configureBenefitLabel())
        
        informationStackView.addArrangedSubview(benefitInformationStack)
        
        guard let fullScoreSubjects = benefit.fullScoreSubjects else { return }
        
        for subject in fullScoreSubjects {
            let subjectLabel: UILabel = UILabel()
            subjectLabel.font = FontManager.shared.font(for: .additionalInformation)
            subjectLabel.textColor = UIColor(hex: "#787878")
            subjectLabel.numberOfLines = 0
            subjectLabel.lineBreakMode = .byWordWrapping
            subjectLabel.text = "• \(subject)"
            benefitInformationStack.addArrangedSubview(subjectLabel)
        }
    }
    
    private func configureBenefitLabel() -> UILabel {
        guard let benefit = self.benefit else { return UILabel() }
        let benefitLabel: UILabel = UILabel()
        benefitLabel.font = FontManager.shared.font(for: .additionalInformation)
        benefitLabel.textColor = .black
        benefitLabel.numberOfLines = 0
        benefitLabel.lineBreakMode = .byWordWrapping
        
        let benefitText = benefit.isBVI ? "БВИ" : "100 баллов за ЕГЭ по одному из следующих предметов:"
        
        benefitLabel.text = benefit.admissionRule?.summary ?? "Льгота: \(benefitText)"
        
        return benefitLabel
    }
    
    private func configurationConfirmationSubjects() {
        guard
            let confirmationSubjects = benefit?.confirmationSubjects,
                confirmationSubjects.count > 0
        else { return }

        let subjectsStackView: UIStackView = UIStackView()
        subjectsStackView.axis = .vertical
        subjectsStackView.spacing = 7
        subjectsStackView.distribution = .fill
        subjectsStackView.alignment = .leading
        
        subjectsStackView.addArrangedSubview(configureConfirmationLabel(score: confirmationSubjects[0].score))
        
        for subject in confirmationSubjects {
            let subjectLabel: UILabel = UILabel()
            subjectLabel.font = FontManager.shared.font(for: .additionalInformation)
            subjectLabel.textColor = UIColor(hex: "#787878")
            subjectLabel.numberOfLines = 0
            subjectLabel.lineBreakMode = .byWordWrapping
            subjectLabel.text = "• \(subject.subject)"
            subjectsStackView.addArrangedSubview(subjectLabel)
        }
        
        informationStackView.addArrangedSubview(subjectsStackView)
    }
    
    private func configureConfirmationLabel(score: Int) -> UILabel {
        let confirmationLabel: UILabel = UILabel()
        confirmationLabel.font = FontManager.shared.font(for: .commonInformation)
        confirmationLabel.textColor = .black
        confirmationLabel.numberOfLines = 0
        confirmationLabel.lineBreakMode = .byWordWrapping
        
        confirmationLabel.text = "Для подтверждения олимпиады необходимо сдать ЕГЭ на \(score) баллов по одному из следующих предметов:"
        
        return confirmationLabel
    }
}
