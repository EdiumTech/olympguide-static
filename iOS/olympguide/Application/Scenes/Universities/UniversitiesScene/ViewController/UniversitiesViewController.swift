//
//  UniversitiesViewController.swift
//  olympguide
//
//  Created by Tom Tim on 22.12.2024.
//

import UIKit
import Combine

// MARK: - Constants
fileprivate enum Constants {
    enum Colors {
        static let refreshTint = UIColor.systemCyan
        static let searchButtonTint = UIColor.black
        static let tableViewBackground = UIColor.white
        static let titleLabelTextColor = UIColor.black
    }
    
    enum Dimensions {
        static let titleLabelTopMargin: CGFloat = 25
        static let titleLabelLeftMargin: CGFloat = 20
        static let searchButtonSize: CGFloat = 33
        static let searchButtonRightMargin: CGFloat = 20
        static let tableViewTopMargin: CGFloat = 13
    }
    
    enum Strings {
        static let universitiesTitle = "ВУЗы"
        static let backButtonTitle = "ВУЗы"
    }
    
    enum Images {
        static let searchIcon: String =  "magnifyingglass"
    }
}

class UniversitiesViewController : UIViewController, WithSearchButton {
    @InjectSingleton
    var filtersManager: FiltersManagerProtocol
    
    @InjectSingleton
    var favoritesManager: FavoritesManagerProtocol
    
    @InjectSingleton
    var authManager: AuthManagerProtocol
    
    // MARK: - VIP
    var interactor: (UniversitiesDataStore & UniversitiesBusinessLogic)?
    var router: UniversitiesRoutingLogic?
    
    var filterItems: [FilterItem] = []
    var selectedParams: [ParamType: SingleOrMultipleArray<Param>] = [:]
    
    // MARK: - Variables
    private let tableView: UICustomTbleView = UICustomTbleView()
    private lazy var dataSource: UniversitiesDataSource = UniversitiesDataSource()
    private let refreshControl: UIRefreshControl = UIRefreshControl()
    
    private let titleLabel: UILabel = UILabel()
    
    lazy var filterSortView: FilterSortView = FilterSortView()
    
    var universities: [UniversityViewModel] = []
    private var cancellables = Set<AnyCancellable>()
    private var didSetInitialContentOffset = false
    
    // MARK: - Lifecycle
    override func viewDidLoad() {
        super.viewDidLoad()

        extendedLayoutIncludesOpaqueBars = true
        
        setupFilterItems()
        setupDataSource()
        configureNavigationBar()
        configureRefreshControl()
        setupFilterSortView()
        configureTableView()
        setupAuthBindings()
        
        loadUniversities()
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)

        guard !didSetInitialContentOffset else { return }
        didSetInitialContentOffset = true
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            tableView.layoutIfNeeded()
            tableView.setContentOffset(
                CGPoint(x: 0, y: -tableView.adjustedContentInset.top),
                animated: false
            )
        }
    }
    
    func loadUniversities() {
        dataSource.isShimmering = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { [weak self] in
            guard
                let self,
                dataSource.isShimmering == true
            else
            { return }
            tableView.reloadData()
        }
        
        let request = Universities.Load.Request(params: selectedParams)
        interactor?.loadUniversities(with: request)
    }
    
    private func setupFilterItems() {
        filterItems = filtersManager.getData(for: type(of: self))
        
        for item in filterItems {
            selectedParams[item.paramType] = SingleOrMultipleArray<Param>(isMultiple: item.isMultipleChoice)
        }
    }
}

// MARK: - UI Configuration
extension UniversitiesViewController {
    private func configureNavigationBar() {
        let backItem = UIBarButtonItem(
            title: Constants.Strings.backButtonTitle,
            style: .plain,
            target: nil,
            action: nil
        )
        navigationItem.backBarButtonItem = backItem
        
        navigationItem.title = Constants.Strings.universitiesTitle
        if #available(iOS 26.0, *) {
            navigationItem.largeTitle = Constants.Strings.universitiesTitle
            navigationItem.largeTitleDisplayMode = .inline
        } else {
            navigationItem.largeTitleDisplayMode = .always
        }
        
        guard let navigationController = self.navigationController as? NavigationBarViewController else {return}
        navigationController.searchButtonPressed = { [weak self] sender in
            self?.router?.routeToSearch()
        }
    }
    
    func configureRefreshControl() {
        refreshControl.tintColor = Constants.Colors.refreshTint
        refreshControl.addTarget(self, action: #selector(handleRefresh), for: .valueChanged)
    }
    
    // MARK: - Private funcs
    private func configureTableView() {
        view.addSubview(tableView)
        
        tableView.frame = view.bounds
        
        dataSource.register(in: tableView)
        
        tableView.refreshControl = refreshControl
        
        tableView.addFilterSortView(
            filterSortView,
            bottom: 0
        )
    }
    
    @objc
    private func handleRefresh() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            [weak self] in
            self?.loadUniversities()
            self?.refreshControl.endRefreshing()
        }
    }
}

// MARK: - UITableViewDataSource & UITableViewDelegate
extension UniversitiesViewController {
    private func setupDataSource() {
        dataSource.viewController = self
        
        dataSource.onFavoriteUniversityTapped = { [weak self] indexPath, isFavorite in
            self?.favoriteUniversityTapped(indexPath, isFavorite)
        }
        
        dataSource.onUniversitySelect = { [weak self] index in
            self?.router?.routeToUniversity(for: index)
        }
    }
    
    func favoriteUniversityTapped(_ indexPath: IndexPath, _ isFavorite: Bool) {
        if isFavorite {
            self.universities[indexPath.row].like = true
            guard
                let model = self.interactor?.universityModel(at: indexPath.row)
            else { return }
            favoritesManager.addUniversityToFavorites(model: model)
        } else {
            self.universities[indexPath.row].like = false
            let id = self.universities[indexPath.row].universityID
            favoritesManager.removeUniversityFromFavorites(universityID: id)
        }
    }
    
}

// MARK: - UniversitiesDisplayLogic
extension UniversitiesViewController : UniversitiesDisplayLogic {
    func displayUniversities(with viewModel: Universities.Load.ViewModel) {
        universities = viewModel.universities
        for i in 0..<universities.count {
            let universityID = universities[i].universityID
            let like = universities[i].like
            universities[i].like = isFavorite(univesityID: universityID, serverValue: like)
        }
        
        dataSource.isShimmering = false
        
        DispatchQueue.main.async {
            self.tableView.reloadData()
            self.refreshControl.endRefreshing()
        }
    }
    
    func displaySetFavorite(at index: Int, isFavorite: Bool) {
        let image = isFavorite ?
            AllConstants.Common.Images.like :
            AllConstants.Common.Images.unlike
        
        let indexPath = IndexPath(row: index, section: 0)
        self.universities[index].like = isFavorite
        
        guard let cell = tableView.cellForRow(at: indexPath) as? UniversityTableViewCell else { return }
        cell.universityView.favoriteButton.setImage(image, for: .normal)
        
//        if self.universities[index].like == isFavorite { return }
//        self.universities[index].like = isFavorite
//        self.tableView.reloadRows(
//            at: [IndexPath(row: index, section: 0)],
//            with: .automatic
//        )
    }
}

// MARK: - OptionsViewControllerDelegate
extension UniversitiesViewController : OptionsViewControllerDelegate {
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
        
        selectedParams[paramType] = filterItems[index].selectedParams
        
        loadUniversities()
    }
}

// MARK: - Filterble
extension UniversitiesViewController : Filterble {
    func deleteFilter(forItemAt index: Int) {
        let item = filterItems[index]
        selectedParams[item.paramType]?.clear()
        loadUniversities()
    }
}


// MARK: - Combine
extension UniversitiesViewController {
    private func setupAuthBindings() {
        authManager.isAuthenticatedPublisher
                .receive(on: DispatchQueue.main)
                .sink { [weak self] isAuth in
                    if isAuth {
                        self?.loadUniversities()
                    }
                }.store(in: &cancellables)
    }
    
    private func isFavorite(univesityID: Int, serverValue: Bool) -> Bool {
        favoritesManager.isUniversityFavorited(
            universityID: univesityID,
            serverValue: serverValue
        )
    }
}
