//
//  OlympiadTableViewCell.swift
//  olympguide
//
//  Created by Tom Tim on 09.01.2025.
//

import UIKit
import Combine

class OlympiadTableViewCell: UICellWithFavoriteButton {
    typealias Constants = AllConstants.OlympiadTableViewCell
    typealias Common = AllConstants.Common
    
    // MARK: - Variables
    static let identifier = "OlympiadTableViewCell"
    
    private let nameLabel = UILabel()
    private let levelAndProfileLabel = UILabel()
    private let benefitLabel: UILabel = UILabel()
    private let separatorLine: UIView = UIView()
    private let shimmerLayer: UIShimmerView = UIShimmerView()
    
    // MARK: - Lifecycle
    override init(style: UITableViewCell.CellStyle, reuseIdentifier: String?) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        configureUI()
    }
    
    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    private func configureUI() {
        backgroundColor = .white
        configureLevelAndProfileLabel()
        configureFavoriteButton()
        configureNameLabel()
        configureBenefitLabel()
        configureSeparotorLine()
        configureShimmerLayer()
    }
    
    private func configureNameLabel() {
        nameLabel.font = FontManager.shared.font(for: .commonInformation)
        nameLabel.numberOfLines = 0
        nameLabel.lineBreakMode = .byWordWrapping
        nameLabel.textColor = .black
        
        contentView.addSubview(nameLabel)
        
        nameLabel.pinTop(to: levelAndProfileLabel.bottomAnchor, Constants.Dimensions.nameLabelTopMargin)
        nameLabel.pinLeft(to: contentView.leadingAnchor, Common.Dimensions.horizontalMargin)
        nameLabel.pinRight(to: favoriteButton.leadingAnchor, Common.Dimensions.horizontalMargin)
    }
    
    private func configureLevelAndProfileLabel() {
        levelAndProfileLabel.font = FontManager.shared.font(for: .additionalInformation)
        levelAndProfileLabel.textColor = Common.Colors.additionalText
        
        contentView.addSubview(levelAndProfileLabel)

        levelAndProfileLabel.pinTop(to: contentView.topAnchor, Constants.Dimensions.nameAndProfileTopMargin)
        levelAndProfileLabel.pinLeft(to: contentView.leadingAnchor,Common.Dimensions.horizontalMargin)
        levelAndProfileLabel.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
    }
    
    private func configureFavoriteButton() {
        favoriteButton.addTarget(
            self,
            action: #selector(favoriteButtonTapped(_:)),
            for: .touchUpInside
        )
        
        contentView.addSubview(favoriteButton)
        
        favoriteButton.pinTop(to: levelAndProfileLabel.bottomAnchor, Constants.Dimensions.buttonTopMargin)
        favoriteButton.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
        favoriteButton.setWidth(Common.Dimensions.favoriteButtonSize)
        favoriteButton.setHeight(Common.Dimensions.favoriteButtonSize)
    }
    
    private func configureBenefitLabel() {
        benefitLabel.font = FontManager.shared.font(for: .additionalInformation)
        benefitLabel.textColor = Common.Colors.additionalText

        contentView.addSubview(benefitLabel)
        
        benefitLabel.pinTop(to: nameLabel.bottomAnchor, Constants.Dimensions.benefitLabelTopMargin)
        benefitLabel.pinLeft(to: contentView.leadingAnchor, Common.Dimensions.horizontalMargin)
        benefitLabel.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
        benefitLabel.pinBottom(to: contentView.bottomAnchor, Constants.Dimensions.benefitLabelBottomMargin)
    }
    
    private func configureSeparotorLine() {
        separatorLine.backgroundColor = Common.Colors.separator
        
        contentView.addSubview(separatorLine)
        
        separatorLine.pinLeft(to: contentView.leadingAnchor, Common.Dimensions.horizontalMargin)
        separatorLine.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
        separatorLine.pinBottom(to: contentView.bottomAnchor)
        separatorLine.setHeight(Common.Dimensions.separatorHeight)
    }
    
    // MARK: - Private funcs
    private func configureShimmerLayer() {
        contentView.addSubview(shimmerLayer)
        shimmerLayer.pinTop(to: contentView.topAnchor, Constants.Dimensions.shimmerTopMargin)
        shimmerLayer.pinLeft(to: contentView.leadingAnchor, Common.Dimensions.horizontalMargin)
        shimmerLayer.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
        shimmerLayer.pinBottom(to: contentView.bottomAnchor, Constants.Dimensions.shimmerBottomMargin)
        shimmerLayer.setHeight(Constants.Dimensions.shimmerHeight)
        shimmerLayer.layer.cornerRadius = Constants.Dimensions.shimmerRadius
    }
    
    // MARK: - Methods
    func configure(
        with viewModel: OlympiadViewModel,
        isFaforiteButtonVisible: Bool = true
    ) {
        nameLabel.text = viewModel.name
        levelAndProfileLabel.text = viewModel.level.isEmpty ? viewModel.profile : "\(viewModel.level) уровень | \(viewModel.profile)"
        benefitLabel.text = nil
        shimmerLayer.isHidden = true
        shimmerLayer.stopAnimating()
        shimmerLayer.removeAllConstraints()
        isUserInteractionEnabled = true
        let newImage = viewModel.like ? Common.Images.like :Common.Images.unlike
        favoriteButton.setImage(newImage, for: .normal)
        favoriteButton.isHidden = authManager.isAuthenticated ? false : true
        favoriteButton.tag = viewModel.olympiadId
        
        favoriteButton.isHidden = !authManager.isAuthenticated || isFavoriteButtonHidden

    }
    
    func configure(
        with viewModel: OlympiadWithBenefitViewModel
    ) {
        nameLabel.text = viewModel.olympiadName
        let level = viewModel.olympiadLevel > 0 ? "\(String(repeating: "I", count: viewModel.olympiadLevel)) уровень" : "Уровень в условиях"
        levelAndProfileLabel.text = "\(level) | \(viewModel.olympiadProfile)"
        let diploma = viewModel.minDiplomaLevel == 1
            ? Constants.Strings.winnerText
            : Constants.Strings.prizeText
        let benefit = viewModel.isBVI ? "БВИ" : "100 баллов"
        let grade = viewModel.minClass.map { "\($0) класс" } ?? "Класс в условиях"
        benefitLabel.text = viewModel.admissionRule?.summary ?? "\(grade) | \(diploma) | \(benefit)"
        shimmerLayer.isHidden = true
        shimmerLayer.stopAnimating()
        shimmerLayer.removeAllConstraints()
        
        isUserInteractionEnabled = true
        
        isFavoriteButtonHidden = true
    }
    
    func configure(with viewModel: DiplomaViewModel) {
        nameLabel.text = viewModel.olympiadName
        let level = viewModel.olympiadLevel > 0 ? "\(String(repeating: "I", count: viewModel.olympiadLevel)) уровень" : "Уровень в условиях"
        levelAndProfileLabel.text = "\(level) | \(viewModel.olympiadProfile)"
        let diploma = viewModel.level == 1
            ? Constants.Strings.winnerText
            : Constants.Strings.prizeText
        benefitLabel.text = "\(viewModel.diplomaClass) класс | \(diploma)"
        
        shimmerLayer.isHidden = true
        shimmerLayer.stopAnimating()
        shimmerLayer.removeAllConstraints()
        
        isUserInteractionEnabled = true
        
        isFavoriteButtonHidden = true
    }
    
    func configureShimmer() {
        shimmerLayer.isHidden = false
        shimmerLayer.startAnimating()
        isUserInteractionEnabled = false
    }
    
    func hideSeparator(_ hide: Bool) {
        separatorLine.isHidden = hide
    }
    
    // MARK: - Objc funcs
    @objc private func favoriteButtonTapped(_ sender: UIButton) {
        let isFavorite = favoriteButton.image(for: .normal) == Common.Images.like
        let newImage = isFavorite ? Common.Images.unlike : Common.Images.like
        favoriteButton.setImage(newImage, for: .normal)
        favoriteButtonTapped?(sender, !isFavorite)
    }
}
