"""
Parameterized generator for GH302_appsmith_36249.

Source PR:    https://github.com/appsmithorg/appsmith/pull/36249
Source Issue: https://github.com/appsmithorg/appsmith/issues/35148

Seed varies: renames 'able' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH302_appsmith_36249'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH302_appsmith_36249'
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        files = self._base_workspace()
        # Apply seed-based renaming to prevent direct memorization
        suffixes = ["", "_alt", "_impl"]
        suffix = suffixes[seed % len(suffixes)]
        if suffix:
            for fpath in list(files.keys()):
                files[fpath] = files[fpath].replace('able', 'able' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH302_appsmith_36249',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'appsmithorg/appsmith',
                "pr_number": 36249,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/appsmithorg/appsmith/pull/36249",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'app/client/cypress/e2e/Regression/ServerSide/GenerateCRUD/MongoURI_Spec.ts': 'import {\n  agHelper,\n  appSettings,\n  assertHelper,\n  dataSources,\n  deployMode,\n  draggableWidgets,\n  locators,\n  table,\n} from "../../../../support/Objects/ObjectsCore";\nimport { Widgets } from "../../../../support/Pages/DataSources";\nimport EditorNavigation, {\n  EntityType,\n  AppSidebarButton,\n  AppSidebar,\n} from "../../../../support/Pages/EditorNavigation";\nimport PageList from "../../../../support/Pages/PageList";\n\ndescribe(\n  "Validate Mongo URI CRUD with JSON Form",\n  { tags: ["@tag.Datasource"] },\n  () => {\n    let dsName: any;\n\n    it("1. Create DS & Generate CRUD template", () => {\n      dataSources.NavigateToDSCreateNew();\n      agHelper.GenerateUUID();\n      cy.get("@guid").then((uid) => {\n        dataSources.CreatePlugIn("MongoDB");\n        dsName = "Mongo" + uid;\n        agHelper.RenameWithInPane(dsName, false);\n        dataSources.FillMongoDatasourceFormWithURI();\n        dataSources.TestSaveDatasource();\n        AppSidebar.navigate(AppSidebarButton.Editor);\n        PageList.AddNewPage("Generate page with data");\n        agHelper.GetNClick(dataSources._selectDatasourceDropdown);\n        agHelper.GetNClickByContains(dataSources._dropdownOption, dsName);\n\n        assertHelper.AssertNetworkStatus("@getDatasourceStructure"); //Making sure table dropdown is populated\n        agHelper.GetNClick(dataSources._selectTableDropdown, 0, true);\n        agHelper.GetNClickByContains(dataSources._dropdownOption, "mongomart");\n        GenerateCRUDNValidateDeployPage(\n          "/img/products/mug.jpg",\n          "Coffee Mug",\n          `Kitchen`,\n          4,\n        );\n\n        deployMode.NavigateBacktoEditor();\n        table.WaitUntilTableLoad(0, 0, "v2");\n        //Should not be able to delete ds until app is published again\n        //coz if app is published & shared then deleting ds may cause issue, So!\n        dataSources.DeleteDatasourceFromWithinDS(dsName as string, 409);\n      });\n    });\n\n    it("2. Verify Update data from Deploy page - on mongomart - existing record", () => {\n      //Update documents query to handle the int _id data\n      EditorNavigation.SelectEntityByName("UpdateQuery", EntityType.Query);\n      agHelper.EnterValue(`{ _id: {{data_table.selectedRow._id}}}`, {\n        propFieldName: "",\n        directInput: false,\n        inputFieldName: "Query",\n      });\n      deployMode.DeployApp(locators._widgetInDeployed(draggableWidgets.TABLE));\n      agHelper.GetNAssertElementText(\n        locators._textWidgetInDeployed,\n        "mongomart Data",\n      );\n      //Validating loaded table\n      table.SelectTableRow(2, 0, true, "v2");\n      agHelper.AssertElementExist(dataSources._selectedRow);\n      table.ReadTableRowColumnData(2, 0, "v2", 200).then(($cellData) => {\n        expect($cellData).to.be.empty;\n      });\n      table.ReadTableRowColumnData(2, 6, "v2", 2000).then(($cellData) => {\n        expect($cellData).to.eq("WiredTiger T-shirt");\n      });\n      table.ReadTableRowColumnData(2, 7, "v2", 200).then(($cellData) => {\n        expect($cellData).to.eq("Apparel");\n      });\n\n      table.SelectTableRow(8, 0, true, "v2");\n      deployMode.ClearJSONFieldValue("Slogan");\n      deployMode.ClearJSONFieldValue("Category");\n\n      agHelper.ClickButton("Update");\n      agHelper.AssertElementAbsence(locators._toastMsg); //Validating fix for Bug 14063\n      for (let i = 7; i <= 8; i++) {\n        table.ReadTableRowColumnData(8, i, "v2").then(($cellData) => {\n          expect($cellData).to.be.empty;\n        });\n      }\n      deployMode.EnterJSONInputValue(\n        "Slogan",\n        "Write Your Story with Elegance: The Pen of Choice!",\n      );\n      agHelper.GetNClick(deployMode._jsonFormNumberFieldByName("Stars", "up")); //1\n      agHelper.GetNClick(deployMode._jsonFormNumberFieldByName("Stars", "up")); //2\n      agHelper.GetNClick(deployMode._jsonFormNumberFieldByName("Stars", "up")); //3\n\n      agHelper.ClickButton("Update");\n      agHelper.AssertElementAbsence(locators._toastMsg); //Validating fix for Bug 14063\n      table.ReadTableRowColumnData(8, 8, "v2", 2000).then(($cellData) => {\n        expect($cellData).to.eq(\n          "Write Your Story with Elegance: The Pen of Choice!",\n        );\n      });\n      table.ReadTableRowColumnData(8, 5, "v2", 200).then(($cellData) => {\n        expect($cellData).to.eq("3");\n      });\n    });\n\n    it("3. Verify Add/Insert from Deploy page - on MongoMart - new record - few validations", () => {\n      agHelper.GetNClick(dataSources._addIcon);\n      agHelper.Sleep();\n      //agHelper.AssertElementVisibility(locators._jsonFormWidget, 1); //Insert Modal\n      agHelper.AssertElementVisibility(\n        locators._visibleTextDiv("Insert Document"),\n      );\n\n      agHelper.AssertElementEnabledDisabled(\n        locators._buttonByText("Submit") + "/parent::div",\n        0,\n        false,\n      );\n      agHelper.ClickButton("Submit");\n      for (let i = 0; i <= 1; i++) {\n        table.ReadTableRowColumnData(i, 6, "v2").then(($cellData) => {\n          expect($cellData).contains("Coffee Mug");\n        });\n      }\n    });\n\n    it("4. Verify Delete from Deploy page - on MongoMart - newly added record", () => {\n      agHelper.ClickButton("Delete", 0);\n      agHelper.AssertElementVisibility(locators._modal);\n      agHelper.AssertElementVisibility(\n        dataSources._visibleTextSpan(\n          "Are you sure you want to delete this document?",\n        ),\n      );\n      agHelper.ClickButton("Confirm");\n      assertHelper.AssertNetworkStatus("@postExecute", 200);\n      assertHelper.AssertNetworkStatus("@postExecute", 200);\n      table.ReadTableRowColumnData(0, 6, "v2", 200).then(($cellData) => {\n        expect($cellData).to.eq("Coffee Mug");\n      });\n      table.ReadTableRowColumnData(1, 6, "v2", 200).then(($cellData) => {\n        expect($cellData).to.eq("Track Jacket");\n      });\n    });\n\n    it("5 Verify Filter & Search & Download from Deploy page - on MongoMart - existing record", () => {\n      table.SearchTable("Swag");\n      agHelper.Sleep(2500); //for search to load\n      for (let i = 0; i <= 1; i++) {\n        table.ReadTableRowColumnData(i, 6, "v2").then(($cellData) => {\n          expect($cellData).to.eq("Swag");\n        });\n      }\n      table.ResetSearch();\n\n      table.OpenNFilterTable("title", "contains", "USB");\n      for (let i = 0; i < 3; i++) {\n        table.ReadTableRowColumnData(i, 5, "v2").then(($cellData) => {\n          expect($cellData).contains("USB");\n        });\n      }\n      table.CloseFilter();\n\n      table.DownloadFromTable("Download as CSV");\n      table.ValidateDownloadNVerify("data_table.csv", "USB Stick (Green)");\n\n      table.DownloadFromTable("Download as Excel");\n      table.ValidateDownloadNVerify("data_table.xlsx", "USB Stick (Leaf)");\n      table.OpenFilter();\n      table.RemoveFilter();\n      agHelper\n        .GetText(table._filtersCount)\n        .then(($filters) => expect($filters).to.eq("Filters"));\n    });\n\n    it("6. Suggested Widget - Table", () => {\n      table.SelectTableRow(8, 0, true, "v2");\n      agHelper.GetNClick(\n        deployMode._jsonFormNumberFieldByName("Stars", "down"),\n      ); //2\n      agHelper.GetNClick(\n        deployMode._jsonFormNumberFieldByName("Stars", "down"),\n      ); //1\n      agHelper.GetNClick(\n        deployMode._jsonFormNumberFieldByName("Stars", "down"),\n      ); //0\n      agHelper.ClickButton("Update");\n\n      deployMode.NavigateBacktoEditor();\n      table.WaitUntilTableLoad(0, 0, "v2");\n      PageList.AddNewPage();\n      dataSources.CreateQueryForDS(dsName);\n      dataSources.ValidateNSelectDropdown("Collection", "", "mongomart");\n      dataSources.RunQuery({ toValidateResponse: false });\n      dataSources.AddSuggestedWidget(Widgets.Table);\n      table.ReadTableRowColumnData(0, 3, "v2").then((cellData) => {\n        expect(cellData).to.eq("1");\n      });\n    });\n  },\n);\n\nfunction GenerateCRUDNValidateDeployPage(\n  col1Text: string,\n  col6Text: string,\n  col7Text: string,\n  idIndex: number,\n) {\n  agHelper.GetNClick(dataSources._generatePageBtn);\n  assertHelper.AssertNetworkStatus("@replaceLayoutWithCRUDPage", 201);\n  agHelper.AssertContains("Successfully generated a page"); // Commenting this since FindQuery failure appears sometimes\n  assertHelper.AssertNetworkStatus("@getActions", 200);\n  assertHelper.AssertNetworkStatus("@postExecute", 200);\n  agHelper.ClickButton("Got it");\n  assertHelper.AssertNetworkStatus("@updateLayout", 200);\n  appSettings.OpenPaneAndChangeTheme("Pacific");\n  deployMode.DeployApp(locators._widgetInDeployed(draggableWidgets.TABLE));\n\n  //Validating loaded table\n  agHelper.AssertElementExist(dataSources._selectedRow);\n  table.ReadTableRowColumnData(0, 1, "v2", 2000).then(($cellData) => {\n    expect($cellData).to.eq(col1Text);\n  });\n  table.ReadTableRowColumnData(0, 6, "v2", 200).then(($cellData) => {\n    expect($cellData).to.eq(col6Text);\n  });\n  table.ReadTableRowColumnData(0, 7, "v2", 200).then(($cellData) => {\n    expect($cellData).to.eq(col7Text);\n  });\n\n  //Validating loaded JSON form\n  cy.xpath(locators._buttonByText("Update")).then((selector) => {\n    cy.wrap(selector)\n      .invoke("attr", "class")\n      .then((classes) => {\n        //cy.log("classes are:" + classes);\n        expect(classes).not.contain("bp3-disabled");\n      });\n  });\n  dataSources.AssertJSONFormHeader(0, idIndex, "Id", "", true);\n}\n',
        }
