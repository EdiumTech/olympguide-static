import UIKit

final class AddDiplomaViewController: PersonalFormController, NonTabBarVC {
    private let olympiad: OlympiadModel
    init(with olympiad: OlympiadModel) { self.olympiad = olympiad; super.init(nibName:nil,bundle:nil) }
    required init?(coder:NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func viewDidLoad() {
        super.viewDidLoad(); title = "Добавить диплом"
        DiplomaForm.configure(self,olympiad:olympiad) { [weak self] in self?.navigationController?.popToRootViewController(animated:true) }
    }
}
