/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { FormView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";

export class UsersFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }

    async onClickFetchUsers(ev) {
        ev.preventDefault();
        try {
            const result = await this.orm.call(
                'users.users',
                'fetch_supabase_users',
                [],
                {}
            );
            
            if (result.success) {
                this.notification.add('Success', {
                    type: 'success',
                    sticky: false,
                });
                // Update the list view without page refresh
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'users.users',
                    view_mode: 'list,form',
                    target: 'current',
                    context: {},
                });
            } else {
                this.notification.add(result.error || 'Error', {
                    type: 'danger',
                    sticky: false,
                });
            }
        } catch (error) {
            this.notification.add('Error', {
                type: 'danger',
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
