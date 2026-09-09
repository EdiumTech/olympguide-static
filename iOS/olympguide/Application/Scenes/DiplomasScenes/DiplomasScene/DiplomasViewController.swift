//
//  DiplomasViewController.swift
//  olympguide
//
//  Created by Tom Tim on 23.03.2025.
//

import UIKit

protocol WithPlusButton { }

final class DiplomasViewController: UIViewController, WithPlusButton {
    var interactor: DiplomasBusinessLogic?
    var router: DiplomasRoutingLogic?
    
    var diplomas: [DiplomaViewModel] = []
    
    private let tableView: UICustomTbleView = UICustomTbleView()
    private let dataSource: DiplomasDataSource = DiplomasDataSource()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        configureUI()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        interactor?.loadDiplomas(with: .init())
    }
    
    func configureUI() {
        view.backgroundColor = .white
        configureNavigationBar()
        configureTableView()
    }
    
    private func configureNavigationBar() {
        navigationController?.navigationBar.prefersLargeTitles = true
        navigationItem.largeTitleDisplayMode = .always
        navigationItem.title = "Мои дипломы"
        let backItem = UIBarButtonItem(title: "Дипломы", style: .plain, target: nil, action: nil)
        navigationItem.backBarButtonItem = backItem
        guard let navigationController = navigationController as? NavigationBarViewController else { return }
        navigationController.plusButtonPressed = { [weak self] sender in
            self?.router?.routeToAddDiploma()
        }
    }
    
    private func configureTableView() {
        view.addSubview(tableView)
        tableView.frame = view.bounds
        tableView.contentInset = UIEdgeInsets(
            top: 0,
            left: 0,
            bottom: 50,
            right: 0
        )
        tableView.showsVerticalScrollIndicator = false
        tableView.separatorStyle = .none
        tableView.backgroundColor = .white
        
        let button = LoadDiplomaButton(title: "Подгрузить дипломы")
        let v = UIView()
        v.addSubview(button)
        button.pinLeft(to: v, 20)
        button.pinTop(to: v, 13)
        let matching = UIButton(type: .system)
        matching.setTitle("Куда подходят мои дипломы →", for: .normal)
        v.addSubview(matching)
        matching.pinLeft(to: v, 20)
        matching.pinTop(to: button.bottomAnchor, 16)
        matching.pinBottom(to: v, 12)
        matching.addAction(UIAction { [weak self] _ in
            self?.navigationController?.pushViewController(RecommendationsViewController(), animated: true)
        }, for: .touchUpInside)
        tableView.addHeaderView(v)
        dataSource.register(in: tableView)
        dataSource.viewController = self
        button.addTarget(self, action: #selector(syncDiplomas), for: .touchUpInside)
        dataSource.deleteDiplomaAt = { [weak self] indexPath in
            guard let self else { return }
            diplomas.remove(at: indexPath.row)
            tableView.deleteRows(at: [indexPath], with: .automatic)
            
            tableView.backgroundView = getEmptyLabel()
            
            let request = Diplomas.Delete.Request(index: indexPath.row)
            interactor?.deleteDiploma(with: request)
            guard
                let cell = tableView.cellForRow(at: IndexPath(row: diplomas.count - 1, section: 0)) as? OlympiadTableViewCell
            else {
                return
            }
            
            cell.hideSeparator(true)
        }
    }
    
    func getEmptyLabel() -> UILabel? {
        if !diplomas.isEmpty { return nil }
        let emptyLabel = UILabel(frame: self.tableView.bounds)
        emptyLabel.text = "Вы пока не добавили дипломы"
        emptyLabel.textAlignment = .center
        emptyLabel.textColor = .black
        emptyLabel.font = FontManager.shared.font(for: .emptyTableLabel)
        return emptyLabel
    }
    
    @objc func syncDiplomas() {
        interactor?.syncDiplomas(with: Diplomas.Sync.Request())
    }
}

extension DiplomasViewController: DiplomasDisplayLogic {
    func displayLoadDiplomasResult(with viewModel: Diplomas.Load.ViewModel) {
        diplomas = viewModel.diplomas
        
        DispatchQueue.main.async { [weak self] in
            self?.tableView.reloadData()
            self?.tableView.backgroundView = self?.getEmptyLabel()
        }
    }
    
    func displayDeleteDiplomaResult(with viewModel: Diplomas.Delete.ViewModel) { }
}
