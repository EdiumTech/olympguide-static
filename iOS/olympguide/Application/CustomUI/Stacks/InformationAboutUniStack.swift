//
//  InformationAboutUniStack.swift
//  olympguide
//
//  Created by Tom Tim on 12.03.2025.
//

import UIKit
import MessageUI
import SafariServices

final class InformationAboutUniStack: UIStackView {
    var searchButtonAction: (() -> Void)?
    var segmentChanged: ((_: UISegmentedControl) -> Void)?
    
    private let segmentedControl: UISegmentedControl = UISegmentedControl()
    private let webSiteButton: UIInformationButton = UIInformationButton(type: .web)
    private let emailButton: UIInformationButton = UIInformationButton(type: .email)
    private let searchButton: UIClosureButton = {
        let button = UIClosureButton()
        button.setImage(UIImage(systemName: "magnifyingglass"), for: .normal)
        button.tintColor = .black
        button.contentHorizontalAlignment = .fill
        button.contentVerticalAlignment = .fill
        button.imageView?.contentMode = .scaleAspectFit
        return button
    }()
    
    func configure(
        university: UniversityModel,
        filterSortView: FilterSortView
    ) {
        setupSelf()
        
        configureUniversityView(university)
        configureWebSiteButton()
        configureEmailButton()
        addScholarshipsButton(universityID: university.universityID)
        configureProgramLabel()
        configureSegmentedControl()
        configureFilterSortView(filterSortView)
        configureLastSpace()
    }
    
    private func setupSelf() {
        arrangedSubviews.forEach { removeArrangedSubview($0) }
        axis = .vertical
        alignment = .fill
        distribution = .fill
        isLayoutMarginsRelativeArrangement = true
        layoutMargins = UIEdgeInsets(top: 30, left: 20, bottom: 0, right: 20)
    }
    
    private func configureUniversityView(_ university: UniversityModel) {
        let universityView = UIUniversityView()
        universityView.configure(with: university.toViewModel(), 20, 20)
        universityView.favoriteButtonIsHidden = true
        
        addArrangedSubview(universityView)
    }
    
    private func configureWebSiteButton() {
        pinToPrevious(30)
        
        addArrangedSubview(webSiteButton)
        webSiteButton.addTarget(self, action: #selector(openWebPage), for: .touchUpInside)
    }
    
    private func configureEmailButton() {
        pinToPrevious(20)
        
        addArrangedSubview(emailButton)
        emailButton.addTarget(self, action: #selector(openMailCompose), for: .touchUpInside)
    }
    
    private func configureProgramLabel() {
        pinToPrevious(20)
        let programsLabel = UILabel()
        programsLabel.text = "Программы"
        programsLabel.font = FontManager.shared.font(for: .tableTitle)
        
        let horizontalStack = UIStackView()
        horizontalStack.axis = .horizontal
        horizontalStack.alignment = .center
        horizontalStack.distribution = .fill
        
        horizontalStack.addArrangedSubview(programsLabel)
        
        let spacer = UIView()
        spacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        horizontalStack.addArrangedSubview(spacer)
        
        searchButton.action = { [weak self] in
            self?.searchButtonAction?()
        }
        
        searchButton.setWidth(28)
        searchButton.setHeight(28)
        
        horizontalStack.addArrangedSubview(searchButton)
        
        addArrangedSubview(horizontalStack)
    }
    
    private func configureSegmentedControl() {
        pinToPrevious(13)
        
        segmentedControl.insertSegment(
            withTitle: "По направлениям",
            at: 0,
            animated: false
        )
        segmentedControl.insertSegment(
            withTitle: "По факультетам",
            at: 1,
            animated: false
        )
        segmentedControl.selectedSegmentIndex = 0
        segmentedControl.setHeight(35)
        
        let customFont = FontManager.shared.font(for: .commonInformation)
        let customAttributes: [NSAttributedString.Key: Any] = [.font: customFont]
        segmentedControl.setTitleTextAttributes(customAttributes, for: .normal)
        segmentedControl.setTitleTextAttributes(customAttributes, for: .selected)
        segmentedControl.addTarget(
            self,
            action: #selector(segmentChanged(_:)),
            for: .valueChanged
        )
        
        addArrangedSubview(segmentedControl)
    }
    
    private func configureFilterSortView(_ filterSortView: FilterSortView) {
        pinToPrevious(13)
        
        addArrangedSubview(filterSortView)
        filterSortView.pinLeft(to: leadingAnchor)
    }
    
    private func configureLastSpace() {
        let spaceView = UIView()
        spaceView.setHeight(17)
        
        addArrangedSubview(spaceView)
    }
    
    func setEmail(_ email: String) {
        emailButton.setTitle(email, for: .normal)
    }
    
    func setWebPage(_ webPage: String) {
        webSiteButton.setTitle(webPage, for: .normal)
    }
    
    @objc func segmentChanged(_ sender: UISegmentedControl) {
        segmentChanged?(sender)
    }
    
    @objc func openWebPage(sender: UIButton) {
        guard
            let currentVC = self.findViewController(),
            let link = sender.currentTitle
        else { return }
        
        guard let url = URL(string: "https://\(link)") else { return }
        let safariVC = SFSafariViewController(url: url)
        safariVC.modalPresentationStyle = .pageSheet
        currentVC.present(safariVC, animated: true, completion: nil)
    }
}

extension InformationAboutUniStack : MFMailComposeViewControllerDelegate {
    @objc func openMailCompose(sender: UIButton) {
        guard
            let currentVC = self.findViewController()
        else { return }
        
        
        guard MFMailComposeViewController.canSendMail() else {
            currentVC.showAlert(
                with: "На телефоне нет настроенного клиента для отправки электронной почты",
                cancelTitle: "Ок"
            )
            return
        }
        
        let mailVC = MFMailComposeViewController()
        mailVC.mailComposeDelegate = self
        mailVC.setToRecipients([sender.currentTitle ?? ""])
        mailVC.setSubject("Вопрос по поступлению")
        mailVC.setMessageBody("Здравствуйте!", isHTML: false)
        
        currentVC.present(mailVC, animated: true, completion: nil)
    }
    
    func mailComposeController(
        _ controller: MFMailComposeViewController,
        didFinishWith result: MFMailComposeResult,
        error: Error?
    ) {
        controller.dismiss(animated: true, completion: nil)
    }
}
