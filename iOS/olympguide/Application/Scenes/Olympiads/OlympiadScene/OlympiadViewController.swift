//
//  OlympiadViewController.swift
//  olympguide
//
//  Created by Tom Tim on 01.03.2025.
//

import UIKit
import Combine

final class OlympiadViewController: UIViewController, WithBookMarkButton {
    @InjectSingleton
    var filtersManager: FiltersManagerProtocol
    
    @InjectSingleton
    var favoritesManager: FavoritesManagerProtocol
    
    @InjectSingleton
    var authManager: AuthManagerProtocol
    
    var interactor: (OlympiadBusinessLogic & BenefitsByProgramsBusinessLogic)?
    var router: OlympiadRoutingLogic?
    
    var filterSortView: FilterSortView = FilterSortView()
    var filterItems: [FilterItem] = []
    var selectedParams: [ParamType: SingleOrMultipleArray<Param>] = [:]
    
    var groups: [UniWithProgramsWithBenefits] = []
    
    private var cancellables = Set<AnyCancellable>()
    
    private let olympiad: OlympiadModel
    private let informationStackView: InformationAboutOlympStack = InformationAboutOlympStack()
    
    private let tableView: UICustomTbleView = UICustomTbleView()
    private let dataSource: OlympiadDataSource = OlympiadDataSource()
    private let refreshControl: UIRefreshControl = UIRefreshControl()
    
    private var isFavorite: Bool = false
    
    init(with olympiad: OlympiadModel) {
        self.olympiad = olympiad
        
        super.init(nibName: nil, bundle: nil)
    }
    
    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        self.isFavorite = favoritesManager.isOlympiadFavorite(
            olympiadId: olympiad.olympiadID,
            serverValue: olympiad.like
        )
        interactor?.isFavorite = isFavorite
        setupDataSource()
        setupFilterItems()
        configureUI()
        let request = Olympiad.LoadUniversities.Request(olympiadID: olympiad.olympiadID)
        interactor?.loadUniversities(with: request)
    }
    
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        guard let navigationController = navigationController as? NavigationBarViewController else { return }
        let newImageName = isFavorite ? "bookmark.fill" :  "bookmark"
        navigationController.bookMarkButton.setImage(UIImage(systemName: newImageName), for: .normal)
        navigationController.bookMarkButtonPressed = {[weak self] sender in
            guard let self = self else { return }
            self.isFavorite.toggle()
            let newImageName = self.isFavorite ? "bookmark.fill" :  "bookmark"
            sender.setImage(UIImage(systemName: newImageName), for: .normal)
            
            if self.isFavorite {
                favoritesManager.addOlympiadToFavorites(model: olympiad)
            } else {
                favoritesManager.removeOlympiadFromFavorites(olympiadId: self.olympiad.olympiadID)
            }
        }
    }
    
    private func loadPrograms() {
        for (section, group) in groups.enumerated() {
            if group.isExpanded {
                let request = BenefitsByPrograms.Load.Request(
                    olympiadID: olympiad.olympiadID,
                    universityID: groups[section].university.universityID,
                    section: section,
                    params: selectedParams
                )
                interactor?.loadBenefits(with: request)
            }
        }
    }
    
    private func setupFilterItems() {
        filterItems = filtersManager.getData(for: type(of: self))
        for item in filterItems {
            selectedParams[item.paramType] = SingleOrMultipleArray<Param>(isMultiple: item.isMultipleChoice)
        }
    }
}

// MARK: - UI Configuration
extension OlympiadViewController {
    private func configureUI() {
        view.backgroundColor = .white
        
        configureNavigationBar()
        
        setupFilterSortView()
        configureInformatonStack()
        
        configureRefreshControl()
        configureTableView()
    }
    
    private func configureInformatonStack() {
        informationStackView.configure(olympiad, filterSortView)
        informationStackView.searchButtonAction = { [weak self] in
            guard let self else { return }
            router?.routeToSearch(olympiadId: olympiad.olympiadID)
        }
    }
    
    private func configureNavigationBar() {
        navigationItem.largeTitleDisplayMode = .never
        let backItem = UIBarButtonItem(title: "Олимпиада", style: .plain, target: nil, action: nil)
        navigationItem.backBarButtonItem = backItem
    }
    
    private func reloadFavoriteButton() {
        guard let navigationController = navigationController as? NavigationBarViewController else { return }
        let newImageName = isFavorite ? "bookmark.fill" :  "bookmark"
        navigationController.bookMarkButton.setImage(UIImage(systemName: newImageName), for: .normal)
    }
    
    private func configureTableView() {
        view.addSubview(tableView)
        
        tableView.frame = view.bounds
    
        dataSource.register(in: tableView)
        
        tableView.refreshControl = refreshControl

        tableView.addHeaderView(informationStackView)
    }
    
    func configureRefreshControl() {
        refreshControl.tintColor = .systemCyan
        refreshControl.addTarget(self, action: #selector(handleRefresh), for: .valueChanged)
    }
    
    @objc private func handleRefresh() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            guard let self else { return }
            loadPrograms()
            self.refreshControl.endRefreshing()
        }
    }
}

// MARK: - UITableViewDataSource
extension OlympiadViewController {
    private func setupDataSource() {
        dataSource.viewController = self
        
        dataSource.onProgramSelect = { [weak self] indexPath in
            self?.router?.routeToProgram(indexPath: indexPath)
        }
        
        dataSource.onSectionToggle = { [weak self] section in
            self?.toggleSection(at: section)
        }
        
    }
    
    private func toggleSection(at index: Int) {
        
        guard groups.indices.contains(index) else { return }
        if !groups[index].isExpanded {
            let request = BenefitsByPrograms.Load.Request(
                olympiadID: olympiad.olympiadID,
                universityID: groups[index].university.universityID,
                section: index,
                params: selectedParams
            )
            interactor?.loadBenefits(with: request)
        }
    }
}

// MARK: - OlympiadDisplayLogic
extension OlympiadViewController : OlympiadDisplayLogic {
    func displayLoadUniversitiesResult(with viewModel: Olympiad.LoadUniversities.ViewModel) {
        groups = viewModel.universities.map {
            UniWithProgramsWithBenefits(university: $0)
        }
        
        let message = UILabel()
        message.text = olympiad.academicYear == nil
            ? "Программы с подтверждёнными условиями льгот пока не найдены."
            : "Условия льгот для дипломов этого сезона пока не подтверждены. Программы появятся после проверки правил вузов."
        message.numberOfLines = 0
        message.textAlignment = .center
        message.textColor = .secondaryLabel
        message.font = .preferredFont(forTextStyle: .body)
        message.frame = CGRect(x: 20, y: 0, width: tableView.bounds.width - 40, height: 110)
        tableView.tableFooterView = groups.isEmpty ? message : nil
        informationStackView.searchButton.isEnabled = true
        
        DispatchQueue.main.async { [weak self] in
            self?.tableView.reloadData()
        }
    }
    
    func displaySetFavorite(to isFavorite: Bool) {
        self.isFavorite = isFavorite
        reloadFavoriteButton()
    }
}

// MARK: - BenefitsByProgramsDisplayLogic
extension OlympiadViewController : BenefitsByProgramsDisplayLogic {
    func displayLoadBenefitsResult(with viewModel: BenefitsByPrograms.Load.ViewModel) {
        guard groups.indices.contains(viewModel.section) else { return }
        groups[viewModel.section].programs = viewModel.benefits
        let id = groups[viewModel.section].university.universityID
        if !dataSource.toggle(to: id, in: tableView) {
            DispatchQueue.main.async { [weak self] in
                self?.tableView.reloadData()
            }
        }
    }
}

extension OlympiadViewController : OptionsViewControllerDelegate {
    func didSelectOption(
        _ indices: Set<Int>,
        _ optionsNames: [OptionViewModel],
        paramType: ParamType?
    ) {
        guard let paramType = paramType else { return }
        guard let index = filterItems.firstIndex(where: { $0.paramType == paramType }) else { return }
        
        filterItems[index].selectedIndices = indices
        
        filterItems[index].selectedParams.clear()
        for option in optionsNames {
            if let param = Param(paramType: paramType, option: option) {
                filterItems[index].selectedParams.add(param)
            }
        }
        
        selectedParams[paramType]?.clear()
        for param in filterItems[index].selectedParams.array {
            selectedParams[paramType]?.add(param)
        }
        
        loadPrograms()
    }
}

// MARK: - Filterble
extension OlympiadViewController : Filterble {
    func deleteFilter(forItemAt index: Int) {
        let item = filterItems[index]
        selectedParams[item.paramType]?.clear()
        
        loadPrograms()
    }
}
