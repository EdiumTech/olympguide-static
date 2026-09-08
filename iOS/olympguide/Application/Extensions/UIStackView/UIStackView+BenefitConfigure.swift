//
//  UIStackView+BenefitConfigure.swift
//  olympguide
//
//  Created by Tom Tim on 05.03.2025.
//

import UIKit

extension UIStackView {
    func configure(
        with benefit: ProgramWithBenefitsViewModel.BenefitInformationViewModel
    ) {
        self.arrangedSubviews.forEach { $0.removeFromSuperview() }
        self.distribution = .fillEqually
        self.spacing = 3
        self.alignment = .center
        self.layer.cornerRadius = 8
        self.backgroundColor = UIColor(hex: "#E0E8FE")
        self.setHeight(22)
        
        let minclassLabel = UILabel()
        minclassLabel.textColor = .black
        minclassLabel.font = FontManager.shared.font(weight: .regular, size: 15)
        minclassLabel.text = benefit.minClass.map { "\($0) класс" } ?? "Условия"
        minclassLabel.layer.cornerRadius = 8
        minclassLabel.backgroundColor = UIColor(hex: "#E0E8FE")
        minclassLabel.textAlignment = .center
        minclassLabel.layer.masksToBounds = true
        
        let minDiplomaLevelLabel = UILabel()
        minDiplomaLevelLabel.textColor = .black
        minDiplomaLevelLabel.font = FontManager.shared.font(weight: .regular, size: 15)
        minDiplomaLevelLabel.text = benefit.minDiplomaLevel.map { $0 == 1 ? "Побед." : "Приз." } ?? "Диплом"
        minDiplomaLevelLabel.layer.cornerRadius = 8
        minDiplomaLevelLabel.backgroundColor = UIColor(hex: "#E0E8FE")
        minDiplomaLevelLabel.textAlignment = .center
        minDiplomaLevelLabel.layer.masksToBounds = true
        
        let benefitLabel = UILabel()
        benefitLabel.adjustsFontSizeToFitWidth = true
        benefitLabel.minimumScaleFactor = 0.7
        benefitLabel.textColor = .black
        benefitLabel.font = FontManager.shared.font(weight: .regular, size: 15)
        benefitLabel.text = benefit.admissionRule?.benefitTitle ?? (benefit.isBVI ? "БВИ" : "100б.")
        benefitLabel.layer.cornerRadius = 8
        benefitLabel.backgroundColor = UIColor(hex: "#E0E8FE")
        benefitLabel.textAlignment = .center
        benefitLabel.layer.masksToBounds = true
        
        addArrangedSubview(minclassLabel)
        addArrangedSubview(minDiplomaLevelLabel)
        addArrangedSubview(benefitLabel)
    }
}
