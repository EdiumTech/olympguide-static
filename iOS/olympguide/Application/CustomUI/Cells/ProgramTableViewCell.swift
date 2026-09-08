//
//  ProgramTableViewCell.swift
//  olympguide
//
//  Created by Tom Tim on 24.02.2025.
//

import UIKit

final class ProgramTableViewCell: UICellWithFavoriteButton {
    typealias Constants = AllConstants.ProgramTableViewCell
    typealias Common = AllConstants.Common
    
    // MARK: - Variables
    static let identifier = "ProgramTableViewCell"
    
    private let informationStack: UIStackView = UIStackView()
    private let budgtetLabel: UIInformationLabel = UIInformationLabel()
    private let paidLabel: UIInformationLabel = UIInformationLabel()
    private let costLabel: UIInformationLabel = UIInformationLabel()
    private let quantityNoteLabel = UILabel()
    private let subjectsStack: TagsContainerView = TagsContainerView()
    private let separatorLine: UIView = UIView()
    
    var leftConstraint: CGFloat = Constants.Dimensions.leadingMargin {
        didSet {
            for constraint in contentView.constraints {
                if constraint.firstAttribute == .leading || constraint.firstAttribute == .left {
                    constraint.constant = leftConstraint
                }
            }
            contentView.layoutIfNeeded()
        }
    }
    
    // MARK: - Lifecycle
    override init(
        style: UITableViewCell.CellStyle,
        reuseIdentifier: String?
    ) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        configureUI()
    }
    
    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    private func configureUI() {
        configureInformationStack()
        configureFavoriteButton()
        configureBudgetLabel()
        configurePaidLabel()
        configureCostLabel()
        configureQuantityNoteLabel()
        configureSubjectsStack()
        configureSeparatorLine()
    }
    
    private func configureInformationStack() {
        informationStack.axis = .horizontal
        informationStack.alignment = .top
        informationStack.spacing = 0
        
        contentView.addSubview(informationStack)
        
        informationStack.pinTop(to: contentView.topAnchor, Constants.Dimensions.informationTopMargin)
        informationStack.pinLeft(to: contentView.leadingAnchor, leftConstraint)
        informationStack.pinRight(
            to: contentView.trailingAnchor,
            Common.Dimensions.horizontalMargin + Common.Dimensions.favoriteButtonSize + Constants.Dimensions.informationRightMargin
        )
    }
    
    private func configureFavoriteButton() {
        favoriteButton.tintColor = .black
        favoriteButton.contentHorizontalAlignment = .fill
        favoriteButton.contentVerticalAlignment = .fill
        favoriteButton.imageView?.contentMode = .scaleAspectFit
        favoriteButton.setImage(Common.Images.unlike, for: .normal)
        
        contentView.addSubview(favoriteButton)
        
        favoriteButton.pinTop(to: contentView.topAnchor, Constants.Dimensions.informationTopMargin)
        favoriteButton.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
        favoriteButton.setWidth(Common.Dimensions.favoriteButtonSize)
        favoriteButton.setHeight(Common.Dimensions.favoriteButtonSize)
    }
    
    private func configureBudgetLabel() {
        budgtetLabel.setText(regular: Constants.Strings.budgetText)
        
        contentView.addSubview(budgtetLabel)
        
        budgtetLabel.pinTop(to: informationStack.bottomAnchor, Constants.Dimensions.blocksSpacing)
        budgtetLabel.pinLeft(to: contentView.leadingAnchor, leftConstraint)
    }
    
    private func configurePaidLabel() {
        paidLabel.setText(regular: Constants.Strings.paidText)
        
        contentView.addSubview(paidLabel)
        
        paidLabel.pinTop(to: budgtetLabel.bottomAnchor, Constants.Dimensions.spacing)
        paidLabel.pinLeft(to: contentView.leadingAnchor, leftConstraint)
    }
    
    private func configureCostLabel() {
        costLabel.setText(regular: Constants.Strings.costText)
        
        contentView.addSubview(costLabel)
        
        costLabel.pinTop(to: paidLabel.bottomAnchor, Constants.Dimensions.spacing)
        costLabel.pinLeft(to: contentView.leadingAnchor, leftConstraint)
        costLabel.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
        costLabel.numberOfLines = 0
    }

    private func configureQuantityNoteLabel() {
        quantityNoteLabel.font = FontManager.shared.font(for: .additionalInformation)
        quantityNoteLabel.textColor = .secondaryLabel
        quantityNoteLabel.numberOfLines = 0
        contentView.addSubview(quantityNoteLabel)
        quantityNoteLabel.pinTop(to: costLabel.bottomAnchor, Constants.Dimensions.spacing)
        quantityNoteLabel.pinLeft(to: contentView.leadingAnchor, leftConstraint)
        quantityNoteLabel.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
    }
    
    private func configureSubjectsStack() {
        contentView.addSubview(subjectsStack)
        
        subjectsStack.pinTop(to: quantityNoteLabel.bottomAnchor, Constants.Dimensions.blocksSpacing)
        subjectsStack.pinLeft(to: contentView.leadingAnchor, leftConstraint)
        subjectsStack.pinRight(to: contentView.trailingAnchor, 20)
    }
    
    private func configureSeparatorLine() {
        separatorLine.backgroundColor = Common.Colors.separator
        
        contentView.addSubview(separatorLine)
        separatorLine.pinTop(to: subjectsStack.bottomAnchor, Constants.Dimensions.blocksSpacing)
        separatorLine.pinLeft(to: contentView.leadingAnchor, leftConstraint)
        separatorLine.pinRight(to: contentView.trailingAnchor, Common.Dimensions.horizontalMargin)
        separatorLine.setHeight(1)
        separatorLine.pinBottom(to: contentView.bottomAnchor)
    }
    
    func configure(
        with viewModel: ProgramViewModel
    ) {
        informationStack.configure(
            with: viewModel.code,
            and: viewModel.name,
            width: nil
        )
        
        budgtetLabel.setBoldText(viewModel.quantities.budgetText)
        paidLabel.setBoldText(viewModel.quantities.paidText)
        costLabel.setBoldText(viewModel.quantities.costText)
        quantityNoteLabel.text = viewModel.quantities.summaryText
        subjectsStack.configure(
            requiredSubjects: viewModel.requiredSubjects,
            optionalSubjects: viewModel.optionalSubjects ?? [],
            maxWidth: UIScreen.main.bounds.width - (Common.Dimensions.horizontalMargin + leftConstraint)
        )
        
        let isFavorite = viewModel.like
        let newImage = isFavorite ? Common.Images.like : Common.Images.unlike
        
        favoriteButton.tag = viewModel.programID
        
        favoriteButton.setImage(newImage, for: .normal)
        
        favoriteButton.addTarget(self, action: #selector(favoriteButtonTapped(_:)), for: .touchUpInside)
        
        favoriteButton.isHidden = !authManager.isAuthenticated || isFavoriteButtonHidden
        
        separatorLine.isHidden = false
        layoutIfNeeded()
    }
    
    func formatNumber(_ number: Int) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.groupingSeparator = " "
        return formatter.string(from: NSNumber(value: number)) ?? "\(number)"
    }
    
    func hideSeparator(_ isHidden: Bool) {
        separatorLine.isHidden = isHidden
    }
    
    // MARK: - Objc funcs
    @objc private func favoriteButtonTapped(_ sender: UIButton) {
        let isFavorite = favoriteButton.image(for: .normal) == Common.Images.like
        let newImage = isFavorite ? Common.Images.unlike : Common.Images.like
        favoriteButton.setImage(newImage, for: .normal)
        favoriteButtonTapped?(sender, !isFavorite)
    }
}
