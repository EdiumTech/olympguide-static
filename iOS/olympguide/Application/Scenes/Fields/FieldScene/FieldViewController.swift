//
//  FieldViewController.swift
//  olympguide
//
//  Created by Tom Tim on 04.03.2025.
//

import UIKit
import Combine

final class FieldViewController: UIViewController {
    @InjectSingleton
    var filtersManager: FiltersManagerProtocol
    
    @InjectSingleton
    var favoritesManager: FavoritesManagerProtocol
    
    @InjectSingleton
    var authManager: AuthManagerProtocol
    
    private var cancellables = Set<AnyCancellable>()
    
    var interactor: FieldBusinessLogic?
    var router: FieldRoutingLogic?
    
    var selectedParams: [ParamType: SingleOrMultipleArray<Param>] = [:]
    
    private let field: GroupOfFieldsModel.FieldModel
    
    private let informationStackView: InformationAboutFieldStack = InformationAboutFieldStack()
    
    private let tableView: UICustomTbleView = UICustomTbleView()
    private let dataSource: FieldDataSource = FieldDataSource()
    private let refreshControl: UIRefreshControl = UIRefreshControl()
    
    var programs: [ProgramsByUniversityViewModel] = []
    
    init(for field: GroupOfFieldsModel.FieldModel) {
        self.field = field
        super.init(nibName: nil, bundle: nil)
    }
    
    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setuoDataSource()
        configureUI()
        loadPrograms()
    }
    
    func loadPrograms() {
        let request = Field.LoadPrograms.Request(
            fieldID: field.fieldId,
            params: selectedParams
        )
        interactor?.loadPrograms(with: request)
    }
}

// MARK: - UI Configurations
extension FieldViewController {
    private func configureUI() {
        view.backgroundColor = .white
        configureNavigationBar()
        configureInformationStackView()
        configureRefreshControl()
        configureTableView()
    }
    
    private func configureNavigationBar() {
        navigationItem.largeTitleDisplayMode = .never
        title = field.code
        let backItem = UIBarButtonItem(
            title: field.code,
            style: .plain,
            target: nil,
            action: nil
        )
        navigationItem.backBarButtonItem = backItem
    }
    
    private func configureInformationStackView() {
        informationStackView.configure(
            with: field
        )
        
        informationStackView.searchTapped = { [weak self] in
            guard let self else { return }
            router?.routeToSearch(fieldId: field.fieldId)
        }
    }
    
    private func configureRefreshControl() {
        refreshControl.tintColor = .systemCyan
        refreshControl.addTarget(
            self,
            action: #selector(handleRefresh),
            for: .valueChanged
        )
    }
    
    private func configureTableView() {
        view.addSubview(tableView)
        
        tableView.frame = view.bounds
        
        tableView.register(
            ProgramTableViewCell.self,
            forCellReuseIdentifier: ProgramTableViewCell.identifier
        )
        
        tableView.register(
            UIUniversityHeaderCell.self,
            forCellReuseIdentifier: UIUniversityHeaderCell.identifier
        )
        
        tableView.dataSource = dataSource
        tableView.delegate = dataSource

        tableView.refreshControl = refreshControl

        tableView.addHeaderView(informationStackView)
    }
    
    // MARK: - Actions
    @objc
    private func handleRefresh() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            guard let self else { return }
            loadPrograms()
            self.refreshControl.endRefreshing()
        }
    }
}

// MARK: - UITableViewDataSource
extension FieldViewController {
    private func setuoDataSource() {
        dataSource.viewController = self
        
        dataSource.onFavoriteProgramTapped = { [weak self] indexPath, isFavorite in
            self?.favoriteButtonTapped(indexPath, isFavorite)
        }
        
        dataSource.routeToProgram = { [weak self] indexPath in
            self?.router?.routeToProgram(indexPath: indexPath)
        }
    }
    
    func favoriteButtonTapped(_ indexPath: IndexPath, _ isFavorite: Bool) {
        programs[indexPath.section].programs[indexPath.row].like = isFavorite
        
        let program = programs[indexPath.section].programs[indexPath.row]
        if !isFavorite {
            favoritesManager.removeProgramFromFavorites(programID: program.programID)
        } else {
            guard
                let university = interactor?.getUniversity(at: indexPath.section),
                let program = interactor?.getProgram(at: indexPath)
            else { return }
            favoritesManager.addProgramToFavorites(university, program)
        }
    }
}

// MARK: - FieldDisplayLogic
extension FieldViewController : FieldDisplayLogic {
    func displaySetFavoriteResult(at indexPath: IndexPath, _ isFavorite: Bool) {
        if programs[indexPath.section].programs[indexPath.row].like == isFavorite { return }
        programs[indexPath.section].programs[indexPath.row].like = isFavorite
        
        self.tableView.reloadData()
    }
    
    func displayLoadProgramsResult(with viewModel: Field.LoadPrograms.ViewModel) {
        programs = viewModel.programs
        
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            let message = UILabel()
            message.text = "Вузы с программами по этому направлению не найдены."
            message.numberOfLines = 0
            message.textAlignment = .center
            message.font = .preferredFont(forTextStyle: .body)
            message.textColor = .secondaryLabel
            message.frame = CGRect(x: 20, y: 0, width: self.tableView.bounds.width - 40, height: 110)
            self.tableView.tableFooterView = self.programs.isEmpty ? message : nil
            self.tableView.reloadData()
            self.refreshControl.endRefreshing()
        }
    }
}

// MARK: - Combine
extension FieldViewController {
    private func setupAuthBindings() {
        authManager.isAuthenticatedPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] isAuth in
                if isAuth {
                    self?.loadPrograms()
                }
            }.store(in: &cancellables)
    }
}
