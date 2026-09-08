//
//  FieldsViewController.swift
//  olympguide
//
//  Created by Tom Tim on 11.01.2025.
//

import UIKit

// MARK: - Constants
fileprivate enum Constants {
    enum Colors {
        static let refreshTint = UIColor.systemCyan
        static let searchButtonTint = UIColor.black
        static let tableViewBackground = UIColor.white
        static let titleLabelTextColor = UIColor.black
    }
    
    enum Fonts {
    }
    
    enum Dimensions {
        static let titleLabelTopMargin: CGFloat = 25
        static let titleLabelLeftMargin: CGFloat = 20
        static let searchButtonSize: CGFloat = 33
        static let searchButtonRightMargin: CGFloat = 20
        static let tableViewTopMargin: CGFloat = 13
    }
    
    enum Strings {
        static let fieldsTitle = "Направления"
        static let backButtonTitle = "   "
    }
    
    enum Images {
        static let searchIcon: String = "magnifyingglass"
    }
}

class FieldsViewController: UIViewController, WithSearchButton {
    @InjectSingleton
    var filtersManager: FiltersManagerProtocol
    
    // MARK: - VIP
    var interactor: (FieldsDataStore & FieldsBusinessLogic)?
    var router: FieldsRoutingLogic?
    
    var filterItems: [FilterItem] = []
    
    private var selectedParams: [ParamType: SingleOrMultipleArray<Param>] = [:]
    
    // MARK: - Variables
    private let tableView: UICustomTbleView = UICustomTbleView()
    private let dataSource: FieldsDataSource = FieldsDataSource()
    private let refreshControl: UIRefreshControl = UIRefreshControl()
    
    lazy var filterSortView: FilterSortView = FilterSortView()
    
    var fields: [GroupOfFieldsViewModel] = []
    private var didSetInitialContentOffset = false
    
    // MARK: - Lifecycle
    override func viewDidLoad() {
        super.viewDidLoad()
        extendedLayoutIncludesOpaqueBars = true
        setupFilterItems()
        configureUI()
        loadFields()
        setupDataSource()
        let backItem = UIBarButtonItem(
            title: Constants.Strings.backButtonTitle,
            style: .plain,
            target: nil,
            action: nil
        )
        navigationItem.backBarButtonItem = backItem
        
        if #available(iOS 15.0, *) {
            tableView.sectionHeaderTopPadding = 0
        }
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
    
    private func loadFields() {
        let request = Fields.Load.Request(params: selectedParams)
        interactor?.loadFields(with: request)
    }
    
    private func setupFilterItems() {
        filterItems = filtersManager.getData(for: type(of: self))
        for item in filterItems {
            selectedParams[item.paramType] = SingleOrMultipleArray<Param>(isMultiple: item.isMultipleChoice)
        }
    }
}

// MARK: - UI Configuration
extension FieldsViewController {
    private func configureUI() {
        configureNavigationBar()
        configureRefreshControl()
        setupFilterSortView()
        configureTableView()
    }
    
    private func configureNavigationBar() {
        navigationItem.title = Constants.Strings.fieldsTitle
        if #available(iOS 26.0, *) {
            navigationItem.largeTitle = Constants.Strings.fieldsTitle
            navigationItem.largeTitleDisplayMode = .inline
        } else {
            navigationItem.largeTitleDisplayMode = .always
        }
        
        if let navigationController = self.navigationController as? NavigationBarViewController {
            navigationController.searchButtonPressed = { [weak self] _ in
                self?.router?.routeToSearch()
            }
        }
    }
    
    func configureRefreshControl() {
        refreshControl.tintColor = Constants.Colors.refreshTint
        refreshControl.addTarget(self, action: #selector(handleRefresh), for: .valueChanged)
    }
    
    private func configureTableView() {
        view.addSubview(tableView)
        
        tableView.frame = view.bounds
        
        tableView.register(
            FieldTableViewCell.self,
            forCellReuseIdentifier: FieldTableViewCell.identifier
        )
        tableView.register(
            UIFieldHeaderCell.self,
            forCellReuseIdentifier: UIFieldHeaderCell.identifier
        )
        
        tableView.dataSource = dataSource
        tableView.delegate = dataSource
        
        tableView.addFilterSortView(filterSortView)
    }
    
    // MARK: - Actions
    @objc
    private func handleRefresh() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            [weak self] in
            self?.loadFields()
            self?.refreshControl.endRefreshing()
        }
    }
}

// MARK: - UITableViewDataSource
extension FieldsViewController {
    private func setupDataSource() {
        dataSource.viewController = self
        
        dataSource.routeToField = { [weak self] indexPath in
            self?.router?.routeToField(for: indexPath)
        }
    }
}

// MARK: - FieldsDisplayLogic
extension FieldsViewController : FieldsDisplayLogic {
    func displayFields(with viewModel: Fields.Load.ViewModel) {
        fields = viewModel.groupsOfFields
        
        DispatchQueue.main.async {
            self.tableView.reloadData()
            self.refreshControl.endRefreshing()
        }
    }
}

// MARK: - Filterble
extension FieldsViewController : Filterble {
    func deleteFilter(forItemAt index: Int) {
        let item = filterItems[index]
        selectedParams[item.paramType]?.clear()
        
        loadFields()
    }
}

// MARK: - OptionsViewControllerDelegate
extension FieldsViewController : OptionsViewControllerDelegate {
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
        
        let request = Fields.Load.Request(params: selectedParams)
        interactor?.loadFields(with: request)
    }
}
