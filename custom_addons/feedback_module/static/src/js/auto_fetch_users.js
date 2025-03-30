/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { FormView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class UsersFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClickFetchUsers(ev) {
        ev.preventDefault();
        try {
            const result = await this.orm.call(
                "users.users",
                "fetch_supabase_users",
                [],
                {}
            );
            this.notification.add("Fetched Supabase users", {
                type: "success",
                sticky: false,
            });
            window.location.reload();
        } catch (error) {
            this.notification.add("Error fetching Supabase users", {
                type: "danger",
                sticky: false,
            });
            console.error("Error fetching Supabase users:", error);
        }
    }
}

export const UsersFormView = {
    ...FormView,
    Controller: UsersFormController,
    // Reference the custom QWeb template. See XML below.
    template: "feedback_module.UsersFormView",
    searchMenuTypes: [],
    recordOptions: {
        mode: "edit",
    },
};

registry.category("views").add("users_form", UsersFormView);
