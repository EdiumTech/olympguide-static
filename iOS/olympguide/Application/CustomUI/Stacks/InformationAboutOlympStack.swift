//
//  InformationAboutOlympStack.swift
//  olympguide
//
//  Created by Tom Tim on 12.03.2025.
//

import UIKit
import SafariServices

final class InformationAboutOlympStack: UIStackView {
    typealias Constants = AllConstants.InformationAboutOlympStack
    typealias Common = AllConstants.Common

    private var olympiad: OlympiadModel?
    var searchButtonAction: (() -> Void)?
    
    let searchButton: UIClosureButton = {
        let button = UIClosureButton()
        button.setImage(Common.Images.search, for: .normal)
        button.tintColor = Common.Colors.text
        button.contentHorizontalAlignment = .fill
        button.contentVerticalAlignment = .fill
        button.imageView?.contentMode = .scaleAspectFit
        return button
    }()
    
    func configure(
        _ olympiad: OlympiadModel,
        _ filterSortView: FilterSortView
    ) {
        self.olympiad = olympiad
        
        setupSelf()
        configureOlympiadNameLabel()
        configureOlympiadInformation()
        if let year = olympiad.academicYear {
            let status = UILabel()
            status.text = "РСОШ " + year + (olympiad.registryStatus == "draft" ? " · Проект перечня" : "")
            status.numberOfLines = 0; status.font = .preferredFont(forTextStyle: .subheadline)
            status.textColor = .secondaryLabel
            addArrangedSubview(status)
            if let subjects = olympiad.subjects, subjects != olympiad.profile {
                let label = UILabel(); label.text = "Предметы и направления: " + subjects
                label.numberOfLines = 0; label.font = .preferredFont(forTextStyle: .subheadline)
                addArrangedSubview(label)
            }
            let source = UIClosureButton()
            source.setTitle("Перечень РСОШ", for: .normal); source.setTitleColor(.systemBlue, for: .normal)
            source.action = { [weak self] in
                guard let url = URL(string: "https://rsr-olymp.ru/news/123") else { return }
                self?.findViewController()?.present(SFSafariViewController(url: url), animated: true)
            }
            addArrangedSubview(source)
        }
        addCalendarButton(olympiadID: olympiad.olympiadID)
        configureProgramsLabel()
        configureFilterSortView(filterSortView)
    }
    
    private func setupSelf() {
        arrangedSubviews.forEach { removeArrangedSubview($0) }
        axis = .vertical
        spacing = Constants.Dimensions.stackSpacing
        distribution = .fill
        alignment = .leading
        
        isLayoutMarginsRelativeArrangement = true
        layoutMargins = UIEdgeInsets(
            top: Constants.Dimensions.layoutMarginTop,
            left: Constants.Dimensions.layoutMarginHorizontal,
            bottom: Constants.Dimensions.layoutMarginBottom,
            right: Constants.Dimensions.layoutMarginHorizontal
        )
    }
    
    private func configureOlympiadNameLabel() {
        guard let olympiad = self.olympiad else { return }
        let olympiadNameLabel = UILabel()
        olympiadNameLabel.font = FontManager.shared.font(weight: .medium, size: 17.0)
        olympiadNameLabel.numberOfLines = 0
        olympiadNameLabel.lineBreakMode = .byWordWrapping
        olympiadNameLabel.text = olympiad.name
        
        olympiadNameLabel.calculateHeight()
        addArrangedSubview(olympiadNameLabel)
    }
    
    private func configureOlympiadInformation() {
        let olympiadInformationStack = UIStackView()
        
        olympiadInformationStack.axis = .vertical
        olympiadInformationStack.spacing = Constants.Dimensions.olympiadInfoSpacing
        olympiadInformationStack.distribution = .fill
        olympiadInformationStack.alignment = .fill
        
        olympiadInformationStack.addArrangedSubview(configureLevelLabel())
        olympiadInformationStack.addArrangedSubview(configureProfileLabel())
        
        addArrangedSubview(olympiadInformationStack)
    }
    
    private func configureLevelLabel() -> UILabel {
        guard let olympiad = self.olympiad else { return UILabel() }
        let levelLabel = UILabel()
        levelLabel.font = FontManager.shared.font(for: .additionalInformation)
        levelLabel.textColor = Constants.Colors.additionalText
        levelLabel.text = Constants.Strings.levelPrefix + String(repeating: "I", count: olympiad.level)
        
        return levelLabel
    }
    
    private func configureProfileLabel() -> UILabel {
        guard let olympiad = self.olympiad else { return UILabel() }
        let profileLabel = UILabel()
        profileLabel.font = FontManager.shared.font(for: .additionalInformation)
        profileLabel.textColor = Constants.Colors.additionalText
        profileLabel.numberOfLines = 0
        profileLabel.lineBreakMode = .byWordWrapping
        profileLabel.text = Constants.Strings.profilePrefix + olympiad.profile
        profileLabel.calculateHeight()
        return profileLabel
    }
    
    private func configureProgramsLabel() {
        let programsLabel = UILabel()
        
        programsLabel.font = FontManager.shared.font(for: .tableTitle)
        programsLabel.textColor = Constants.Colors.text
        programsLabel.text = Constants.Strings.programsTitle
        addArrangedSubview(programsLabel)
        
        let searchButton = getSearchButton()
        searchButton.action = { [weak self] in
            self?.searchButtonAction?()
        }
        addSubview(searchButton)
        searchButton.pinRight(to: trailingAnchor, Constants.Dimensions.layoutMarginHorizontal)
        searchButton.pinCenterY(to: programsLabel)
    }
    
    private func getSearchButton() -> UIClosureButton {
        searchButton.isEnabled = false
        searchButton.setWidth(Constants.Dimensions.searchButtonSize)
        searchButton.setHeight(Constants.Dimensions.searchButtonSize)
        return searchButton
    }
    
    private func configureFilterSortView(_ filterSortView: FilterSortView) {
        pinToPrevious(Constants.Dimensions.pinToPreviousOffset)
        addArrangedSubview(UIView())
        
        addSubview(filterSortView)
        filterSortView.pinLeft(to: leadingAnchor)
        filterSortView.pinRight(to: trailingAnchor)
        filterSortView.pinBottom(to: bottomAnchor, Constants.Dimensions.pinBottomOffset)
    }
}


