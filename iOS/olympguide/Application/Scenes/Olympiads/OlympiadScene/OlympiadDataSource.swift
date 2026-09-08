//
//  OlympiadDataSource.swift
//  olympguide
//
//  Created by Tom Tim on 12.03.2025.
//

import UIKit

class UniWithProgramsWithBenefits {
    let university: UniversityViewModel
    var programs: [ProgramWithBenefitsViewModel] = []
    var isExpanded: Bool = false
    
    init(university: UniversityViewModel) {
        self.university = university
    }
}

enum ProgramWithBenefitItem {
    case header(UniWithProgramsWithBenefits, Int)
    case cell(ProgramWithBenefitsViewModel, IndexPath)
    case empty
}

final class OlympiadDataSource: NSObject, UITableViewDelegate {
    weak var viewController: OlympiadViewController?
    
    var onProgramSelect: ((IndexPath) -> Void)?
    var onSectionToggle: ((Int) -> Void)?
    
    var programItems: [ProgramWithBenefitItem] {
        guard let groups = viewController?.groups else { return [] }
        var result: [ProgramWithBenefitItem] = []
        for (grouIndex, group) in groups.enumerated() {
            result.append(.header(group, grouIndex))
            guard group.isExpanded else { continue }
            if group.programs.isEmpty { result.append(.empty) }
            for (programIndex, program) in group.programs.enumerated() {
                autoreleasepool {
                    let indexParh = IndexPath(row: programIndex, section: grouIndex)
                    result.append(.cell(program, indexParh))
                }
            }
        }
        return result
    }
    
    func register(in tableView: UITableView) {
        tableView.delegate = self
        tableView.dataSource = self
        
        tableView.register(
            UIProgramWithBenefitsCell.self,
            forCellReuseIdentifier: UIProgramWithBenefitsCell.identifier
        )
        
        tableView.register(
            UIUniversityHeaderCell.self,
            forCellReuseIdentifier: UIUniversityHeaderCell.identifier
        )
    }
}

// MARK: - UITableViewDataSource
extension OlympiadDataSource: UITableViewDataSource {
    func tableView(
        _ tableView: UITableView,
        numberOfRowsInSection section: Int
    ) -> Int {
        return programItems.count
    }
    
    func tableView(
        _ tableView: UITableView,
        cellForRowAt indexPath: IndexPath
    ) -> UITableViewCell {
        
        let item = programItems[indexPath.row]
        
        switch item {
        case .empty:
            let cell = UITableViewCell(style: .default, reuseIdentifier: nil)
            var content = cell.defaultContentConfiguration()
            content.text = "Программы с подтверждённой связью с этой олимпиадой по выбранным условиям не найдены."
            content.textProperties.numberOfLines = 0
            content.textProperties.color = .secondaryLabel
            cell.contentConfiguration = content
            cell.selectionStyle = .none
            return cell
        case .header(let group, _):
            return configureHeader(tableView, cellForRowAt: indexPath, group: group)
        case .cell(let program, let realIndexPath):
            return configureCell(
                tableView,
                cellForRowAt: indexPath,
                program: program,
                realIndexPath: realIndexPath
            )
        }
    }
    
    private func configureHeader(
        _ tableView: UITableView,
        cellForRowAt indexPath: IndexPath,
        group: UniWithProgramsWithBenefits
    ) -> UITableViewCell {
        guard
            let cell = tableView.dequeueReusableCell(
                withIdentifier: UIUniversityHeaderCell.identifier,
                for: indexPath
            ) as? UIUniversityHeaderCell
        else { return UITableViewCell() }
        
        cell.configure(
            with: group.university,
            isExpanded: group.isExpanded
        )
        
        return cell
    }
    
    private func configureCell(
        _ tableView: UITableView,
        cellForRowAt indexPath: IndexPath,
        program: ProgramWithBenefitsViewModel,
        realIndexPath: IndexPath
    ) -> UITableViewCell {
        guard
            let cell = tableView.dequeueReusableCell(
                withIdentifier: UIProgramWithBenefitsCell.identifier
            ) as? UIProgramWithBenefitsCell
        else {
            return UITableViewCell()
        }
        
        cell.configure(with: program, indexPath: realIndexPath)
        for view in cell.benefitsStack.arrangedSubviews {
            guard let subview = view as? BenefitStackView else { continue }
            subview.createPreviewVC = { indexPath, index in
                let program = program
                let previewVC = BenefitViewController(with: program, index: index)
                return previewVC
            }
        }
        cell.hideSeparator(isSeparatorHidden(indexPath))
        
        return cell
    }
    
    
    func isSeparatorHidden(_ indexPath: IndexPath) -> Bool {
        guard indexPath.row < programItems.count - 1 else { return true }
        
        if case .header = programItems[indexPath.row + 1] {
            return true
        }
        
        return false
    }
    
    func tableView(
        _ tableView: UITableView,
        didSelectRowAt indexPath: IndexPath
    ) {
        tableView.deselectRow(at: indexPath, animated: true)
        
        let item = programItems[indexPath.row]
        
        switch item {
        case .empty: return
        case .header(let group, let section):
            toggleSection(
                at: indexPath,
                group: group,
                section: section,
                in: tableView
            )
        case .cell(_, let realIndexPath):
            tableView.deselectRow(at: indexPath, animated: true)
            onProgramSelect?(realIndexPath)
        }
    }
    
    func toggleSection(
        at indexPath: IndexPath,
        group: UniWithProgramsWithBenefits,
        section: Int,
        in tableView: UITableView
    ) {
        let toggleIndex = indexPath.row
        
        if group.isExpanded {
            group.isExpanded = false
            let programsCount = max(1, group.programs.count)
            var indexPathsToDelete: [IndexPath] = []
            if programsCount > 0 {
                for i in 1...programsCount {
                    indexPathsToDelete.append(IndexPath(row: toggleIndex + i, section: 0))
                }
            }
            
            tableView.beginUpdates()
            tableView.deleteRows(at: indexPathsToDelete, with: .fade)
            tableView.reloadRows(at: [indexPath], with: .none)
            tableView.endUpdates()
        } else {
            onSectionToggle?(section)
        }
        
    }
    
    func toggle(to id: Int, in tableView: UITableView) -> Bool {
        for (toggleIndex, item) in programItems.enumerated() {
            switch item {
            case .header(let group, _):
                guard group.university.universityID == id else { continue }
                if group.isExpanded == true {
                    return false
                }
                tableView.beginUpdates()
                group.isExpanded = true
                let programsCount = max(1, group.programs.count)
                
                var indexPathsToInsert: [IndexPath] = []
                
                if programsCount > 0 {
                    for i in 1...programsCount {
                        indexPathsToInsert.append(IndexPath(row: toggleIndex + i, section: 0))
                    }
                }
                
                tableView.insertRows(at: indexPathsToInsert, with: .fade)
                let indexPath = IndexPath(row: toggleIndex, section: 0)
                
                tableView.reloadRows(at: [indexPath], with: .none)
                tableView.endUpdates()
                return true
            case .cell, .empty:
                continue
            }
        }
        return false
    }
}
