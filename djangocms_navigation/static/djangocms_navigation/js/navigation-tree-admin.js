/**
This is replicated and partially re-factored code from Treebeard,
with specific changes implemented for djangocms-navigation.

Original code found in treebeard-admin.js
**/
(function ($) {
    ACTIVE_NODE_BG_COLOR = '#B7D7E8';
    RECENTLY_MOVED_COLOR = '#FFFF00';
    RECENTLY_MOVED_FADEOUT = '#FFFFFF';
    ABORT_COLOR = '#EECCCC';
    DRAG_LINE_COLOR = '#AA00AA';
    RECENTLY_FADE_DURATION = 2000;

    const EXPANDED_SESSION_KEY = 'expanded-';

    // Add jQuery util for disabling selection
    // Originally taken from jquery-ui (where it is deprecated)
    // https://api.jqueryui.com/disableSelection/
    if($.fn.disableSelection == undefined) {
        $.fn.extend( {
            disableSelection: ( function() {
                var eventType = "onselectstart" in document.createElement( "div" ) ? "selectstart" : "mousedown";
                return function() {
                    return this.on( eventType + ".ui-disableSelection", function( event ) {
                        event.preventDefault();
                    } );
                };
            } )(),
    
            enableSelection: function() {
                return this.off( ".ui-disableSelection" );
            }
        } );
    }

    // This is the basic Node class, which handles UI tree operations for each 'row'
    var Node = function (elem) {
        var $elem = $(elem);
        var node_id = $elem.attr('node');
        var parent_id = $elem.attr('parent');
        var level = parseInt($elem.attr('level'));
        var children_num = parseInt($elem.attr('children-num'));
        var menu_content_id = $("#result_list").data("menuContentId");
        return {
            elem: elem,
            $elem: $elem,
            node_id: node_id,
            parent_id: parent_id,
            level: level,
            expanded_key: EXPANDED_SESSION_KEY + menu_content_id,
            has_children: function () {
                return children_num > 0;
            },
            node_name: function () {
                // Returns the text of the node
                return $elem.find('th a:not(.collapse)').text();
            },
            is_collapsed: function () {
                return $elem.find('a.collapse').hasClass('collapsed');
            },
            is_expanded: function () {
                return $elem.find('a.collapse').hasClass('expanded');
            },
            children: function () {
                return $('tr[parent=' + node_id + ']');
            },
            parent_node: function () {
                // Returns a Node object of the parent
                return new Node($('tr[node=' + parent_id + ']', $elem.parent())[0]);
            },
            collapse: function () {
                // Collapse all child nodes:
                $.each(this.children(),function () {
                    let node = new Node(this);
                    node.collapse();
                }).hide();
            },
            expand: function () {
                // Expand each child node:
                $.each(this.children(), function() {
                    // Check child nodes to see if any of them were hidden in an expanded state,
                    // if so re-expand them:
                    let node = new Node(this);
                    if(node.is_expanded()){
                        node.expand();
                    }
                }).show();
            },
            // collapse_all() and expand_all() show/hide the node + child nodes AND modifies classes:
            // (In practice these functions are only used with the root node)
            collapse_all: function () {
                this.$elem.find('a.collapse').removeClass('expanded').addClass('collapsed');
                $.each(this.children(), function() {
                    let node = new Node(this);
                    node.collapse_all();
                }).hide();
                // clear storage so that on reload go back to default view
                sessionStorage.clear()
            },
            expand_all: function () {
                this.$elem.find('a.collapse').removeClass('collapsed').addClass('expanded');
                $.each(this.children(), function() {
                    let node = new Node(this);
                    node.expand_all();
                }).show();
                // clear storage so that on reload go back to default view
                sessionStorage.clear()
            },
            // Toggle show/hides the node (and child nodes), but does not modify child classes - this is so the 'state' can be perserved.
            toggle: function () {
                if (this.is_collapsed()) {
                    this.expand();
                    // Update classes just for this node:
                    this.$elem.find('a.collapse').removeClass('collapsed').addClass('expanded');
                    this.add_to_session()
                } else {
                    this.collapse();
                    this.$elem.find('a.collapse').removeClass('expanded').addClass('collapsed');
                    this.remove_from_session()
                }
            },
            clone: function () {
                return $elem.clone();
            },
            add_to_session: function () {
                // get or create an array of element ids that are expanded
                let expanded = JSON.parse(sessionStorage.getItem(this.expanded_key)) || []
                expanded.push(this.elem.id)
                sessionStorage.setItem(this.expanded_key, JSON.stringify(expanded))
            },
            remove_from_session: function () {
                let expanded = JSON.parse(sessionStorage.getItem(this.expanded_key)) || []
                // filter the array to remove this element id
                expanded = expanded.filter(elementId =>  elementId !== this.elem.id)
                // also remove any child elements
                if (this.has_children()) {
                    $.each(this.children(), function () {
                        expanded = expanded.filter(elementId => elementId !== this.id)
                    })
                }
                // update the session
                sessionStorage.setItem(this.expanded_key, JSON.stringify(expanded))
            }
        }
    };

    $(document).ready(function () {

        // check the session for a stored state of expanded nodes
        const menuContentId = $("#result_list").data("menuContentId");
        let expanded = JSON.parse(sessionStorage.getItem(EXPANDED_SESSION_KEY + menuContentId))
        if (expanded) {
            expanded.forEach(function (elementId) {
                var node = new Node($.find('#' + elementId)[0])
                node.expand()
                node.$elem.find('a.collapse').removeClass('collapsed').addClass('expanded');
            })
        }

        // begin csrf token code
        // Taken from http://docs.djangoproject.com/en/dev/ref/contrib/csrf/#ajax
        $(document).ajaxSend(function (event, xhr, settings) {
            function getCookie(name) {
                var cookieValue = null;
                if (document.cookie && document.cookie != '') {
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {
                        var cookie = $.trim(cookies[i]);
                        // Does this cookie string begin with the name we want?
                        if (cookie.substring(0, name.length + 1) == (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }

            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                // Only send the token to relative URLs i.e. locally.
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        });
        // end csrf token code


        // Don't activate drag or collapse if GET filters are set on the page
        if ($('#has-filters').val() === "1") {
            return;
        }

        $body = $('body');

        // Drag/drop only can be disabled. This ensures collapsible links are still activated.
        // This is disabled when viewing a preview of a menu.
        if ($('#disable-drag-drop').val() !== "1") {
            // Activate all rows for drag & drop
            // then bind mouse down event
            $('td.drag-handler span').addClass('active').bind('mousedown', function (evt) {
                $ghost = $('<div id="ghost"></div>');
                $drag_line = $('<div id="drag_line"><span></span></div>');
                $ghost.appendTo($body);
                $drag_line.appendTo($body);

                var stop_drag = function () {
                    $ghost.remove();
                    $drag_line.remove();
                    $body.enableSelection().unbind('mousemove').unbind('mouseup');
                    node.elem.removeAttribute('style');
                };

                // Create a clone create the illusion that we're moving the node
                var node = new Node($(this).closest('tr')[0]);
                cloned_node = node.clone();
                node.$elem.css({
                    'background': ACTIVE_NODE_BG_COLOR
                });

                $targetRow = null;
                as_child = false;

                // Now make the new clone move with the mouse
                $body.disableSelection().bind('mousemove',function (evt2) {
                    $ghost.html(cloned_node).css({  // from FeinCMS :P
                        'opacity': .8,
                        'position': 'absolute',
                        'top': evt2.pageY,
                        'left': evt2.pageX - 30,
                        'width': 600
                    });
                    // Iterate through all rows and see where am I moving so I can place
                    // the drag line accordingly
                    rowHeight = node.$elem.height();
                    $('tr', node.$elem.parent()).each(function (index, element) {
                        $row = $(element);
                        rtop = $row.offset().top;
                        // The tooltop will display whether I'm droping the element as
                        // child or sibling
                        $tooltip = $drag_line.find('span');
                        $tooltip.css({
                            'left': node.$elem.width() - $tooltip.width(),
                            'height': rowHeight,
                        });
                        node_top = node.$elem.offset().top;
                        // Check if you are dragging over the same node
                        if (evt2.pageY >= node_top && evt2.pageY <= node_top + rowHeight) {
                            $targetRow = null;
                            $tooltip.text(gettext('Abort'));
                            $drag_line.css({
                                'top': node_top,
                                'height': rowHeight,
                                'borderWidth': 0,
                                'opacity': 0.8,
                                'backgroundColor': ABORT_COLOR
                            });
                        } else
                        // Check if mouse is over this row
                        if (evt2.pageY >= rtop && evt2.pageY <= rtop + rowHeight / 2) {
                            // The mouse is positioned on the top half of a $row
                            $targetRow = $row;
                            as_child = false;
                            $drag_line.css({
                                'left': node.$elem.offset().left,
                                'width': node.$elem.width(),
                                'top': rtop,
                                'borderWidth': '5px',
                                'height': 0,
                                'opacity': 1
                            });
                            $tooltip.text(gettext('As Sibling'));
                        } else if (evt2.pageY >= rtop + rowHeight / 2 && evt2.pageY <= rtop + rowHeight) {
                            // The mouse is positioned on the bottom half of a row
                            $targetRow = $row;
                            target_node = new Node($targetRow[0]);
                            if (target_node.is_collapsed()) {
                                target_node.expand();
                            }
                            as_child = true;
                            $drag_line.css({
                                'top': rtop,
                                'left': node.$elem.offset().left,
                                'height': rowHeight,
                                'opacity': 0.4,
                                'width': node.$elem.width(),
                                'borderWidth': 0,
                                'backgroundColor': DRAG_LINE_COLOR
                            });
                            $tooltip.text(gettext('As child'));
                        }
                    });
                }).bind('mouseup',function () {
                    // prompt user to confirm the move
                    let moveMessage = `${node.elem.parentElement.dataset["moveMessage"]} ${node.node_name()}?`
                    let confirmMove = confirm(moveMessage)
                    if ($targetRow !== null && confirmMove === true) {
                        target_node = new Node($targetRow[0]);
                        if (target_node.node_id !== node.node_id) {

                            // Call $.ajax so we can handle the error
                            // On Drop, make an XHR call to perform the node move
                            $.ajax({
                                url: window.MOVE_NODE_ENDPOINT,
                                type: 'POST',
                                data: {
                                    node_id: node.node_id,
                                    parent_id: target_node.parent_id,
                                    sibling_id: target_node.node_id,
                                    as_child: as_child ? 1 : 0
                                },
                                success: function (data, status, req) {

                                    let level = parseFloat(target_node.$elem.attr('level')) + parseFloat(as_child ? 1 : 0);
                                    // If assigned as a child, set the parent id to the target node id:
                                    let parent_id = as_child ? target_node.node_id : target_node.parent_id;

                                    // Insert and Update node attrs for parent & level (for indentation)
                                    node.$elem
                                        .attr('parent', parent_id)
                                        .attr('level', level);
                                    node.$elem.find('span.spacer').attr('style', `--s-width:${level-1}`)

                                    if(as_child) {
                                        node.$elem.insertAfter(target_node.$elem);
                                    } else {
                                        node.$elem.insertBefore(target_node.$elem);
                                    }

                                },
                                error: function (req, status, error) {
                                    // Leave node as is, let complete handler display error message(s).

                                },
                                complete: function (req, status) {

                                    // Fetch and display any messages:
                                    let csrfToken = document.cookie.match(/csrftoken=([^;]*);?/)[1];
                                    fetch(window.FETCH_MESSAGES_ENDPOINT, {
                                        method: 'GET',
                                        credentials: 'same-origin',
                                        headers: {
                                            'X-CSRFToken': csrfToken,
                                            'Content-Type': 'application/json;charset=utf-8',
                                        },
                                        redirect: 'error',
                                    })
                                    .then(response => response.json())
                                    .then(payload => {

                                        // Check if Django messagelist already visible on page,
                                        // if not create element to append message(s) too:
                                        let msglist = document.getElementsByClassName('messagelist')[0];
                                        if(msglist === undefined){
                                            msglist = document.createElement('ul');
                                            msglist.className = 'messagelist';
                                            // Insert messagelist before main content div:
                                            document.getElementById('content').before(msglist);
                                        }

                                        payload.messages.forEach(message => {
                                            let msg = document.createElement('li');
                                            msg.className = message.level;
                                            msg.innerHTML = message.message;
                                            msg.style.opacity = 1;

                                            msglist.append(msg);

                                            setTimeout(() => {
                                                let fader = setInterval(() => {
                                                    msg.style.opacity -= 0.05;
                                                    if(msg.style.opacity < 0) {
                                                        msg.style.display = "none";
                                                        clearInterval(fader);
                                                    }
                                                }, 20);
                                            }, 5000);
                                        })
                                    })
                                    .catch(err => {
                                        console.log(`Error: Unfortunately there was an error: ${err}`)
                                    });
                                }
                            });
                        }
                    }
                    stop_drag();
                }).bind('keyup', function (kbevt) {
                    // Cancel drag on escape
                    if (kbevt.keyCode === 27) {
                        stop_drag();
                    }
                });
            });
        }

        $('a.collapse').click(function () {
            var node = new Node($(this).closest('tr')[0]); // send the DOM node, not jQ
            node.toggle();
            return false;
        });

        $('.expand-all a').click(function (e) {
            e.preventDefault();
            // Get root node:
            let root_node = new Node($.find('tr[level=1]')[0]);

            // Toggle expand / collapse all:
            if (!this.hasAttribute('class') || $(this).hasClass('collapsed-all') ) {
                root_node.expand_all();
                $(this).addClass('expanded-all').removeClass('collapsed-all').text('-');
            } else {
                root_node.collapse_all();
                $(this).addClass('collapsed-all').removeClass('expanded-all').text('+');
            }
        });

        var hash = window.location.hash;

        if (hash) {
            $(hash + '-id').animate({
                backgroundColor: RECENTLY_MOVED_COLOR
            }, RECENTLY_FADE_DURATION, function () {
                $(this).animate({
                    backgroundColor: RECENTLY_MOVED_FADEOUT
                }, RECENTLY_FADE_DURATION, function () {
                    this.removeAttribute('style');
                });
            });
        }
    });
})(django.jQuery);

// This block is here to handle animation of backgroundColor with jQuery, more information on this stackoverflow thread:
// http://stackoverflow.com/questions/190560/jquery-animate-backgroundcolor/2302005#2302005
(function (d) {
    d.each(["backgroundColor", "borderBottomColor", "borderLeftColor", "borderRightColor", "borderTopColor", "color", "outlineColor"], function (f, e) {
        d.fx.step[e] = function (g) {
            if (!g.colorInit) {
                g.start = c(g.elem, e);
                g.end = b(g.end);
                g.colorInit = true
            }
            g.elem.style[e] = "rgb(" + [Math.max(Math.min(parseInt((g.pos * (g.end[0] - g.start[0])) + g.start[0]), 255), 0), Math.max(Math.min(parseInt((g.pos * (g.end[1] - g.start[1])) + g.start[1]), 255), 0), Math.max(Math.min(parseInt((g.pos * (g.end[2] - g.start[2])) + g.start[2]), 255), 0)].join(",") + ")"
        }
    });
    function b(f) {
        var e;
        if (f && f.constructor == Array && f.length == 3) {
            return f
        }
        if (e = /rgb\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)/.exec(f)) {
            return[parseInt(e[1]), parseInt(e[2]), parseInt(e[3])]
        }
        if (e = /rgb\(\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*\)/.exec(f)) {
            return[parseFloat(e[1]) * 2.55, parseFloat(e[2]) * 2.55, parseFloat(e[3]) * 2.55]
        }
        if (e = /#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})/.exec(f)) {
            return[parseInt(e[1], 16), parseInt(e[2], 16), parseInt(e[3], 16)]
        }
        if (e = /#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])/.exec(f)) {
            return[parseInt(e[1] + e[1], 16), parseInt(e[2] + e[2], 16), parseInt(e[3] + e[3], 16)]
        }
        if (e = /rgba\(0, 0, 0, 0\)/.exec(f)) {
            return a.transparent
        }
        return a[d.trim(f).toLowerCase()]
    }

    function c(g, e) {
        var f;
        do {
            f = d.css(g, e);
            if (f != "" && f != "transparent" || d.nodeName(g, "body")) {
                break
            }
            e = "backgroundColor"
        } while (g = g.parentNode);
        return b(f)
    }

    var a = {aqua: [0, 255, 255], azure: [240, 255, 255], beige: [245, 245, 220], black: [0, 0, 0], blue: [0, 0, 255], brown: [165, 42, 42], cyan: [0, 255, 255], darkblue: [0, 0, 139], darkcyan: [0, 139, 139], darkgrey: [169, 169, 169], darkgreen: [0, 100, 0], darkkhaki: [189, 183, 107], darkmagenta: [139, 0, 139], darkolivegreen: [85, 107, 47], darkorange: [255, 140, 0], darkorchid: [153, 50, 204], darkred: [139, 0, 0], darksalmon: [233, 150, 122], darkviolet: [148, 0, 211], fuchsia: [255, 0, 255], gold: [255, 215, 0], green: [0, 128, 0], indigo: [75, 0, 130], khaki: [240, 230, 140], lightblue: [173, 216, 230], lightcyan: [224, 255, 255], lightgreen: [144, 238, 144], lightgrey: [211, 211, 211], lightpink: [255, 182, 193], lightyellow: [255, 255, 224], lime: [0, 255, 0], magenta: [255, 0, 255], maroon: [128, 0, 0], navy: [0, 0, 128], olive: [128, 128, 0], orange: [255, 165, 0], pink: [255, 192, 203], purple: [128, 0, 128], violet: [128, 0, 128], red: [255, 0, 0], silver: [192, 192, 192], white: [255, 255, 255], yellow: [255, 255, 0], transparent: [255, 255, 255]}
})(django.jQuery);
