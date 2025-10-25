/** @odoo-module **/

import {useEffect, useState, useRef} from "@odoo/owl";

/**
 * @param {string} popupRef
 * @param {string} containerRef
 */
export function useAbsoluteThreedPopUp(popupRef, containerRef) {
    const state = useState({
        visible: false,
        mousePositionX: 0,
        mousePositionY: 0,
        currentId: 0,
    });
    const infoPopupRef = useRef(popupRef);
    const sceneContainerRef = useRef(containerRef);

    useEffect(_popUpPositionRenderer, () => [
        infoPopupRef,
        state.visible,
        state.mousePositionX,
        state.mousePositionY,
        sceneContainerRef,
    ]);

    /**
     * @param {{ el: HTMLDivElement; }} popupRef
     * @param {boolean} showPopUp
     * @param {number} mousePositionX
     * @param {number} mousePositionY
     * @param {{ el: HTMLDivElement; }} sceneContainerRef
     */
    function _popUpPositionRenderer(
        popupRef,
        showPopUp,
        mousePositionX,
        mousePositionY,
        sceneContainerRef
    ) {
        if (showPopUp) {
            const popup = popupRef.el;
            const container = sceneContainerRef.el;
            const containerRect = container.getBoundingClientRect();
            const popupRect = popup.getBoundingClientRect();

            popup.style.top = `${mousePositionY - containerRect.top - 10}px`;
            popup.style.left = `${mousePositionX - containerRect.left - 10}px`;

            if (popupRect.right > containerRect.right) {
                popup.style.left = `${
                    mousePositionX - containerRect.left - popupRect.width - 30
                }px`;
            }
            if (popupRect.bottom > containerRect.bottom) {
                popup.style.top = `${
                    mousePositionY - containerRect.top - popupRect.height - 30
                }px`;
            }
        }
    }

    /**
     * @param {{ clientX: any; clientY: any; }} event
     * @param {any} currentId
     */
    function show(event, currentId) {
        Object.assign(state, {
            visible: true,
            currentId: currentId,
            mousePositionX: event.clientX,
            mousePositionY: event.clientY,
        });
    }

    function hide() {
        Object.assign(state, {
            visible: false,
            mousePositionX: 0,
            mousePositionY: 0,
            currentId: 0,
        });
    }

    return {
        state,
        show,
        hide,
    };
}
